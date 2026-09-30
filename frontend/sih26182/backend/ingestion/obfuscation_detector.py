"""
Obfuscation Detection Module — SIH26182

Pre-processing layer that identifies obfuscation techniques BEFORE the
Laplacian solver runs, and annotates the graph accordingly:

1. CoinJoin Detection      — equal-output entropy analysis (BTC)
2. Nested Exchange Detection — funnel pattern: high fan-in → single VASP
3. P2P/OTC Sink Detection   — terminal nodes with high volume, no outgoing
4. Tornado Cash Detection    — known contract addresses + timing correlation (ETH)

Each detector returns structured annotations. The attribution pipeline uses
these to adjust edge weights or promote nodes to candidate VASPs, making
the Laplacian solver ($Lx = b$) produce physically correct results even
under adversarial obfuscation.
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

import networkx as nx

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Data Classes
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class CoinJoinResult:
    is_coinjoin: bool = False
    confidence: float = 0.0
    coinjoin_type: str = ""          # wasabi_whirlpool | joinmarket | possible
    pool_size: int = 0               # number of equal-value outputs
    num_inputs: int = 0
    output_entropy: float = 0.0
    tx_hash: str = ""

@dataclass
class NestedExchangeResult:
    address: str = ""
    parent_vasp: str = ""
    parent_name: str = ""
    funnel_ratio: float = 0.0
    depositor_count: int = 0
    confidence: float = 0.0
    suggested_tag: str = ""

@dataclass
class P2PSinkResult:
    address: str = ""
    total_volume_btc: float = 0.0
    neighbor_count: int = 0
    is_round_amount: bool = False
    confidence: float = 0.0
    suggested_tag: str = "Suspected P2P/OTC Cash-out Terminal"

@dataclass
class TornadoCashResult:
    detected: bool = False
    deposits: List[dict] = field(default_factory=list)
    withdrawals: List[dict] = field(default_factory=list)
    correlations: List[dict] = field(default_factory=list)

@dataclass
class ObfuscationReport:
    """Aggregated obfuscation analysis for an investigation."""
    coinjoin_transactions: List[CoinJoinResult] = field(default_factory=list)
    nested_exchanges: List[NestedExchangeResult] = field(default_factory=list)
    p2p_sinks: List[P2PSinkResult] = field(default_factory=list)
    tornado_cash: Optional[TornadoCashResult] = None

    @property
    def techniques_detected(self) -> List[str]:
        found = []
        if self.coinjoin_transactions:
            found.append("CoinJoin")
        if self.nested_exchanges:
            found.append("Nested Exchange")
        if self.p2p_sinks:
            found.append("P2P/OTC")
        if self.tornado_cash and self.tornado_cash.detected:
            found.append("Tornado Cash")
        return found

    def to_dict(self) -> dict:
        return {
            "techniques_detected": self.techniques_detected,
            "coinjoin_transactions": [
                {"tx_hash": cj.tx_hash, "type": cj.coinjoin_type,
                 "pool_size": cj.pool_size, "confidence": cj.confidence,
                 "output_entropy": cj.output_entropy}
                for cj in self.coinjoin_transactions
            ],
            "nested_exchanges": [
                {"address": ne.address, "parent_vasp": ne.parent_name,
                 "funnel_ratio": ne.funnel_ratio, "confidence": ne.confidence}
                for ne in self.nested_exchanges
            ],
            "p2p_sinks": [
                {"address": ps.address, "volume_btc": ps.total_volume_btc,
                 "is_round_amount": ps.is_round_amount, "confidence": ps.confidence}
                for ps in self.p2p_sinks
            ],
            "tornado_cash": {
                "detected": self.tornado_cash.detected if self.tornado_cash else False,
                "deposit_count": len(self.tornado_cash.deposits) if self.tornado_cash else 0,
                "correlations": self.tornado_cash.correlations if self.tornado_cash else [],
            },
        }


# ──────────────────────────────────────────────────────────────────────────────
# 1. CoinJoin Detection
# ──────────────────────────────────────────────────────────────────────────────

def detect_coinjoin(tx_obj: dict) -> CoinJoinResult:
    """
    Detect CoinJoin transactions using structural heuristics.

    Heuristic rules (based on Maurer et al. 2017, BlockSci methodology):
    1. >= 3 inputs from DIFFERENT addresses
    2. >= 3 outputs with EQUAL values (within 1% tolerance)
    3. Low Shannon entropy of output value distribution

    Works on raw Blockstream/Mempool.space transaction JSON.
    For synthetic demo data, works on our edge format too.
    """
    tx_hash = tx_obj.get("txid", tx_obj.get("tx_hash", ""))
    inputs = tx_obj.get("vin", [])
    outputs = tx_obj.get("vout", [])

    # Rule 1: Count distinct input addresses
    input_addrs = set()
    for vin in inputs:
        prevout = vin.get("prevout", {})
        addr = prevout.get("scriptpubkey_address", prevout.get("addr", ""))
        if addr:
            input_addrs.add(addr)

    if len(input_addrs) < 3:
        return CoinJoinResult(is_coinjoin=False, tx_hash=tx_hash)

    # Rule 2: Count equal-value output groups
    output_values = []
    for v in outputs:
        val = v.get("value", 0)
        if val > 0:
            output_values.append(val)

    if len(output_values) < 3:
        return CoinJoinResult(is_coinjoin=False, tx_hash=tx_hash)

    # Group outputs by value (bucket to nearest 1000 sats for fee tolerance)
    equal_groups: Dict[int, int] = {}
    for val in output_values:
        bucket = round(val, -3) if val > 10000 else val
        equal_groups[bucket] = equal_groups.get(bucket, 0) + 1

    max_equal_count = max(equal_groups.values()) if equal_groups else 0

    if max_equal_count < 3:
        return CoinJoinResult(is_coinjoin=False, tx_hash=tx_hash)

    # Rule 3: Shannon entropy of output distribution
    total = len(output_values)
    entropy = 0.0
    for count in equal_groups.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)

    # Classification
    if max_equal_count >= 5 and entropy < 1.5:
        cj_type = "wasabi_whirlpool"
    elif max_equal_count >= 3:
        cj_type = "joinmarket"
    else:
        cj_type = "possible_coinjoin"

    confidence = min(0.95, 0.5 + (max_equal_count / 20))

    return CoinJoinResult(
        is_coinjoin=True,
        confidence=round(confidence, 3),
        coinjoin_type=cj_type,
        pool_size=max_equal_count,
        num_inputs=len(input_addrs),
        output_entropy=round(entropy, 3),
        tx_hash=tx_hash,
    )


def detect_coinjoin_from_graph(G: nx.Graph, suspect: str) -> List[CoinJoinResult]:
    """
    Detect CoinJoin-like patterns directly from the NetworkX graph.
    For use with synthetic demo data where we don't have raw tx JSON.

    Identifies nodes that exhibit CoinJoin behavior:
    - High degree (many connections)
    - Multiple edges with identical weights (equal-output pattern)
    """
    results = []

    for node in G.nodes():
        neighbors = list(G.neighbors(node))
        if len(neighbors) < 4:
            continue

        # Get edge weights to neighbors
        edge_weights = []
        for n in neighbors:
            w = G[node][n].get("weight", 0)
            if w > 0:
                edge_weights.append(w)

        if len(edge_weights) < 4:
            continue

        # Count equal-weight groups
        weight_groups: Dict[float, int] = {}
        for w in edge_weights:
            bucket = round(w, 4)
            weight_groups[bucket] = weight_groups.get(bucket, 0) + 1

        max_equal = max(weight_groups.values())
        if max_equal >= 3:
            total = len(edge_weights)
            entropy = 0.0
            for count in weight_groups.values():
                if count > 0:
                    p = count / total
                    entropy -= p * math.log2(p)

            results.append(CoinJoinResult(
                is_coinjoin=True,
                confidence=min(0.95, 0.5 + (max_equal / 20)),
                coinjoin_type="wasabi_whirlpool" if max_equal >= 5 else "joinmarket",
                pool_size=max_equal,
                num_inputs=len(neighbors),
                output_entropy=round(entropy, 3),
                tx_hash=f"cj_node_{node}",
            ))

    return results


# ──────────────────────────────────────────────────────────────────────────────
# 2. Nested Exchange Detection
# ──────────────────────────────────────────────────────────────────────────────

def detect_nested_exchanges(
    G: nx.Graph,
    known_vasps: Set[str],
    tag_repo=None,
) -> List[NestedExchangeResult]:
    """
    Detect nested exchanges via the FUNNEL pattern:
    - High fan-in (many unique depositors sending to this node)
    - Low fan-out (>70% of outgoing volume goes to a single known VASP)
    - Node is NOT already tagged as a known entity

    Nested exchanges are OTC desks or sub-exchanges that use a parent
    exchange's hot wallet for settlement. On-chain, they look like
    intermediaries, but they are the actual cash-out point.
    """
    nested_candidates = []

    for node in G.nodes():
        if node in known_vasps:
            continue

        neighbors = list(G.neighbors(node))
        if len(neighbors) < 3:
            continue

        # Calculate total volume and volume flowing to known VASPs
        total_volume = 0.0
        vasp_volume: Dict[str, float] = {}
        non_vasp_neighbors = 0

        for neighbor in neighbors:
            weight = G[node][neighbor].get("weight", 0)
            total_volume += weight

            if neighbor in known_vasps:
                vasp_volume[neighbor] = vasp_volume.get(neighbor, 0) + weight
            else:
                non_vasp_neighbors += 1

        if total_volume == 0 or not vasp_volume:
            continue

        # Check funnel pattern: >70% of volume flows to one VASP
        for vasp, vol in vasp_volume.items():
            ratio = vol / total_volume
            if ratio >= 0.70 and non_vasp_neighbors >= 3:
                # Lookup parent VASP name
                parent_name = vasp[:16]
                if tag_repo:
                    tag = tag_repo.get_tag(vasp)
                    if tag:
                        parent_name = tag["entity_name"]

                nested_candidates.append(NestedExchangeResult(
                    address=node,
                    parent_vasp=vasp,
                    parent_name=parent_name,
                    funnel_ratio=round(ratio, 3),
                    depositor_count=non_vasp_neighbors,
                    confidence=min(0.90, ratio),
                    suggested_tag=f"Suspected Nested Exchange (via {parent_name})",
                ))

    return nested_candidates


# ──────────────────────────────────────────────────────────────────────────────
# 3. P2P / OTC Cash-out Sink Detection
# ──────────────────────────────────────────────────────────────────────────────

def detect_p2p_cashout_sinks(
    G: nx.Graph,
    suspect: str,
    known_vasps: Set[str],
) -> List[P2PSinkResult]:
    """
    Detect P2P/OTC cash-out terminals via SINK patterns:
    - High incoming volume from suspect's connected component
    - Very low outgoing degree (≤ 2 neighbors — funds stop here)
    - Not a known exchange or VASP
    - Bonus signal: round BTC amounts (0.5, 1.0, 2.0 = OTC trade sizes)
    """
    sinks = []

    # Only consider nodes reachable from suspect
    if nx.is_connected(G):
        reachable = set(G.nodes())
    else:
        reachable = nx.node_connected_component(G, suspect) if suspect in G else set()

    for node in reachable:
        if node == suspect or node in known_vasps:
            continue

        neighbors = list(G.neighbors(node))
        neighbor_count = len(neighbors)

        # Sink: very few connections (dead end)
        if neighbor_count > 2:
            continue

        total_volume = sum(
            G[node][n].get("weight", 0) for n in neighbors
        )

        if total_volume <= 0:
            continue

        # Check for round BTC amounts (P2P OTC indicator)
        round_amounts = [0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 50.0, 100.0]
        is_round = any(abs(total_volume - r) < 0.02 for r in round_amounts)

        confidence = 0.60 if is_round else 0.40

        sinks.append(P2PSinkResult(
            address=node,
            total_volume_btc=round(total_volume, 6),
            neighbor_count=neighbor_count,
            is_round_amount=is_round,
            confidence=confidence,
        ))

    # Rank by volume descending
    sinks.sort(key=lambda s: s.total_volume_btc, reverse=True)
    return sinks[:5]


# ──────────────────────────────────────────────────────────────────────────────
# 4. Tornado Cash Detection (ETH)
# ──────────────────────────────────────────────────────────────────────────────

# Known Tornado Cash contract addresses (Ethereum Mainnet)
TORNADO_CASH_POOLS = {
    "0x12D66f87A04A9E220743712cE6d9bB1B5616B8Fc": {"denomination": 0.1, "token": "ETH"},
    "0x47CE0C6eD5B0Ce3d3A51fdb1C52DC66a7c3c2936": {"denomination": 1.0, "token": "ETH"},
    "0x910Cbd523D972eb0a6f4cAe4618aD62622b39DbF": {"denomination": 10.0, "token": "ETH"},
    "0xA160cdAB225685dA1d56aa342Ad8841c3b53f291": {"denomination": 100.0, "token": "ETH"},
    # Synthetic demo aliases (for offline testing without real contracts)
    "tornado_pool_0.1_ETH": {"denomination": 0.1, "token": "ETH"},
    "tornado_pool_1.0_ETH": {"denomination": 1.0, "token": "ETH"},
    "tornado_pool_10_ETH":  {"denomination": 10.0, "token": "ETH"},
    "tornado_pool_100_ETH": {"denomination": 100.0, "token": "ETH"},
}


def detect_tornado_cash(G: nx.Graph) -> TornadoCashResult:
    """
    Detect Tornado Cash interactions in the graph by checking for
    known contract addresses and performing timing correlation.
    """
    deposits = []
    withdrawals = []

    tc_addresses = set(TORNADO_CASH_POOLS.keys())
    graph_tc_nodes = tc_addresses.intersection(set(G.nodes()))

    if not graph_tc_nodes:
        return TornadoCashResult(detected=False)

    for tc_node in graph_tc_nodes:
        pool_info = TORNADO_CASH_POOLS[tc_node]

        for neighbor in G.neighbors(tc_node):
            edge_data = G[tc_node][neighbor]
            weight = edge_data.get("weight", 0)
            timestamp = edge_data.get("timestamp")

            # Heuristic: if neighbor → TC node, it's a deposit
            # if TC node → neighbor, it's a withdrawal
            # In undirected graph, use weight matching to denomination
            denom = pool_info["denomination"]
            if abs(weight - denom) < denom * 0.05:  # within 5% of pool denomination
                # Could be either deposit or withdrawal; classify by node metadata
                node_kind = G.nodes[neighbor].get("kind", "")
                if node_kind == "suspect" or "suspect" in str(neighbor).lower():
                    deposits.append({
                        "from": neighbor,
                        "pool": tc_node,
                        "denomination": denom,
                        "timestamp": timestamp,
                    })
                else:
                    withdrawals.append({
                        "to": neighbor,
                        "pool": tc_node,
                        "denomination": denom,
                        "timestamp": timestamp,
                    })

    if not deposits and not withdrawals:
        return TornadoCashResult(detected=False)

    # Timing correlation: match deposits to withdrawals
    correlations = correlate_tc_timing(deposits, withdrawals)

    return TornadoCashResult(
        detected=True,
        deposits=deposits,
        withdrawals=withdrawals,
        correlations=correlations,
    )


def correlate_tc_timing(
    deposits: List[dict],
    withdrawals: List[dict],
    time_window_hours: int = 48,
) -> List[dict]:
    """
    Probabilistic linking of Tornado Cash deposits to withdrawals
    via timing analysis. This is the ONLY feasible de-anonymization
    method — ZK proofs make on-chain linking impossible.

    NOTE: Results are PROBABILISTIC. Court-admissible as supporting
    evidence only, not as proof of direct linkage.
    """
    correlations = []

    for dep in deposits:
        for wd in withdrawals:
            # Same denomination pool required
            if dep.get("denomination") != wd.get("denomination"):
                continue

            dep_time = dep.get("timestamp")
            wd_time = wd.get("timestamp")

            if dep_time and wd_time:
                if isinstance(dep_time, datetime) and isinstance(wd_time, datetime):
                    delta = (wd_time - dep_time).total_seconds()
                else:
                    continue

                # Withdrawal must be AFTER deposit
                if delta < 0:
                    continue

                # Within time window
                if delta > time_window_hours * 3600:
                    continue

                hours_gap = delta / 3600
                time_score = max(0.1, 1.0 - (hours_gap / time_window_hours))

                correlations.append({
                    "deposit_from": dep["from"],
                    "withdrawal_to": wd["to"],
                    "denomination_eth": dep["denomination"],
                    "hours_gap": round(hours_gap, 2),
                    "time_correlation_score": round(time_score, 3),
                    "evidence_type": "PROBABILISTIC_TIMING_ONLY",
                })

    correlations.sort(key=lambda c: c["time_correlation_score"], reverse=True)
    return correlations


# ──────────────────────────────────────────────────────────────────────────────
# Unified analysis entry point
# ──────────────────────────────────────────────────────────────────────────────

def analyze_obfuscation(
    G: nx.Graph,
    suspect: str,
    known_vasps: Set[str],
    tag_repo=None,
    chain: str = "BTC",
) -> ObfuscationReport:
    """
    Run all applicable obfuscation detectors on the extracted subgraph.
    Returns a unified ObfuscationReport with all findings.
    """
    report = ObfuscationReport()

    # CoinJoin detection (BTC only, works on graph structure)
    if chain.upper() == "BTC":
        report.coinjoin_transactions = detect_coinjoin_from_graph(G, suspect)

    # Nested exchange detection (any chain)
    report.nested_exchanges = detect_nested_exchanges(G, known_vasps, tag_repo)

    # P2P sink detection (any chain)
    report.p2p_sinks = detect_p2p_cashout_sinks(G, suspect, known_vasps)

    # Tornado Cash (ETH only)
    if chain.upper() == "ETH":
        report.tornado_cash = detect_tornado_cash(G)

    if report.techniques_detected:
        logger.info(
            f"Obfuscation analysis for {suspect}: "
            f"detected [{', '.join(report.techniques_detected)}]"
        )
    else:
        logger.info(f"Obfuscation analysis for {suspect}: no obfuscation patterns detected.")

    return report
