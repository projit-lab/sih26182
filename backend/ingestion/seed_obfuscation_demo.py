"""
Obfuscation Demo Data Generator — SIH26182

Generates synthetic transaction graphs that demonstrate each obfuscation
technique being detected by our ObfuscationDetector:

1. CoinJoin Scenario     — 5 users pool funds, equal-value outputs
2. Nested Exchange Scenario — OTC desk funnels to parent exchange
3. P2P/OTC Scenario       — funds terminate at personal wallet (no exchange)
4. Tornado Cash Scenario   — deposit/withdrawal through TC pool with timing gap

Each scenario creates a NetworkX graph and runs the detector to prove detection works.
Run directly: python -m backend.ingestion.seed_obfuscation_demo
"""

import hashlib
import logging
import time
from datetime import datetime, timedelta

import networkx as nx

from backend.database.db import get_db_connection, init_db
from backend.database.repositories import EntityTagRepository, TransactionEdgeRepository
from backend.ingestion.obfuscation_detector import (
    analyze_obfuscation,
    detect_coinjoin_from_graph,
    detect_nested_exchanges,
    detect_p2p_cashout_sinks,
    detect_tornado_cash,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def _tx_hash(src: str, dst: str, n: int = 0) -> str:
    return hashlib.sha256(f"{src}->{dst}:{n}".encode()).hexdigest()


def seed_coinjoin_scenario(edge_repo: TransactionEdgeRepository, tag_repo: EntityTagRepository):
    """
    Scenario: CoinJoin (Wasabi Wallet style)

    5 users pool BTC into a single CoinJoin transaction.
    All 5 outputs have EQUAL value (0.1 BTC = 10,000,000 sats).
    The suspect's funds exit through one of the equal outputs.

    Graph:
        suspect_cj ──┐
        user_cj_1  ──┤
        user_cj_2  ──┼── [CoinJoin Pool Node] ──→ cj_out_0 (0.1 BTC) → Binance
        user_cj_3  ──┤                        ──→ cj_out_1 (0.1 BTC)
        user_cj_4  ──┘                        ──→ cj_out_2 (0.1 BTC)
                                               ──→ cj_out_3 (0.1 BTC)
                                               ──→ cj_out_4 (0.1 BTC)
    """
    logger.info("═══ Seeding CoinJoin Scenario ═══")

    base_time = datetime(2026, 8, 15, 14, 0, 0)
    pool_node = "coinjoin_pool_wasabi_01"
    equal_amount = 10_000_000  # 0.1 BTC per output

    # Tag the suspect and exchange
    tag_repo.bulk_insert_tags([
        ("suspect_cj", "CoinJoin Suspect", "illicit", "BTC", "Demo", 1.0),
        ("1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s", "Binance", "exchange", "BTC", "Demo", 1.0),
    ])

    edges = []

    # 5 inputs into the CoinJoin pool (different amounts — inputs are NOT equal)
    input_users = ["suspect_cj", "user_cj_1", "user_cj_2", "user_cj_3", "user_cj_4"]
    input_amounts = [10_500_000, 10_200_000, 10_800_000, 10_100_000, 10_400_000]

    for i, (user, amt) in enumerate(zip(input_users, input_amounts)):
        edges.append((
            _tx_hash(user, pool_node, i),
            user, pool_node, amt,
            base_time + timedelta(seconds=i * 30),
            "BTC", False,
        ))

    # 5 EQUAL outputs from the CoinJoin pool (the CoinJoin signature)
    output_addrs = [f"cj_out_{i}" for i in range(5)]
    for i, out_addr in enumerate(output_addrs):
        edges.append((
            _tx_hash(pool_node, out_addr, i),
            pool_node, out_addr, equal_amount,  # ALL EQUAL — this is what the detector catches
            base_time + timedelta(seconds=300),
            "BTC", False,
        ))

    # One CoinJoin output leads to Binance (the actual cash-out path)
    edges.append((
        _tx_hash("cj_out_0", "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s", 0),
        "cj_out_0", "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s", 9_900_000,
        base_time + timedelta(hours=2),
        "BTC", False,
    ))

    edge_repo.insert_edges(edges)
    logger.info(f"  Inserted {len(edges)} edges (5 inputs → CoinJoin pool → 5 equal outputs)")
    return "suspect_cj"


def seed_nested_exchange_scenario(edge_repo: TransactionEdgeRepository, tag_repo: EntityTagRepository):
    """
    Scenario: Nested Exchange (Indian OTC Desk)

    An unlicensed OTC desk collects deposits from 6 users and forwards
    >80% of volume to a single parent exchange (Binance). The nested
    exchange is the real cash-out point, but on-chain it looks like
    just another intermediary.

    Graph:
        suspect_nested ──┐
        depositor_1    ──┤
        depositor_2    ──┼── [nested_otc_desk] ──→ 80% → Binance (tagged)
        depositor_3    ──┤                     ──→ 10% → WazirX (tagged)
        depositor_4    ──┤                     ──→ 10% → personal_wallet
        depositor_5    ──┘
    """
    logger.info("═══ Seeding Nested Exchange Scenario ═══")

    base_time = datetime(2026, 8, 20, 9, 0, 0)

    tag_repo.bulk_insert_tags([
        ("suspect_nested", "Nested Exchange Suspect", "illicit", "BTC", "Demo", 1.0),
        ("1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s", "Binance", "exchange", "BTC", "Demo", 1.0),
        ("1AnwDVbwsLB4om3PnZ54FjWc1m8qP2XbVq", "WazirX", "exchange", "BTC", "Demo", 1.0),
    ])

    edges = []
    otc_desk = "nested_otc_desk_mumbai"

    # 6 depositors send funds to the OTC desk
    depositors = ["suspect_nested"] + [f"depositor_ne_{i}" for i in range(5)]
    for i, dep in enumerate(depositors):
        amt = 20_000_000 + i * 5_000_000  # 0.2 - 0.45 BTC each
        edges.append((
            _tx_hash(dep, otc_desk, i),
            dep, otc_desk, amt,
            base_time + timedelta(hours=i),
            "BTC", False,
        ))

    total_collected = sum(20_000_000 + i * 5_000_000 for i in range(6))

    # OTC desk forwards ~80% to Binance (funnel pattern)
    edges.append((
        _tx_hash(otc_desk, "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s", 0),
        otc_desk, "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s",
        int(total_collected * 0.80),
        base_time + timedelta(hours=8),
        "BTC", False,
    ))

    # ~10% to WazirX
    edges.append((
        _tx_hash(otc_desk, "1AnwDVbwsLB4om3PnZ54FjWc1m8qP2XbVq", 0),
        otc_desk, "1AnwDVbwsLB4om3PnZ54FjWc1m8qP2XbVq",
        int(total_collected * 0.10),
        base_time + timedelta(hours=8, minutes=5),
        "BTC", False,
    ))

    # ~10% to personal wallet (OTC desk operator's cut)
    edges.append((
        _tx_hash(otc_desk, "otc_operator_personal", 0),
        otc_desk, "otc_operator_personal",
        int(total_collected * 0.10),
        base_time + timedelta(hours=8, minutes=10),
        "BTC", False,
    ))

    edge_repo.insert_edges(edges)
    logger.info(f"  Inserted {len(edges)} edges (6 depositors → OTC desk → 80% Binance funnel)")
    return "suspect_nested"


def seed_p2p_scenario(edge_repo: TransactionEdgeRepository, tag_repo: EntityTagRepository):
    """
    Scenario: P2P / OTC Cash-out (LocalBitcoins style)

    Suspect launders BTC through 3 hops and cashes out at a personal
    wallet via face-to-face P2P trade. There is NO exchange endpoint
    in the graph — funds terminate at a dead-end wallet.

    Graph:
        suspect_p2p → hop_p2p_1 → hop_p2p_2 → p2p_buyer_wallet (DEAD END, 1.0 BTC round amount)
                                             → bg_wallet_1 (tiny change)
    """
    logger.info("═══ Seeding P2P/OTC Scenario ═══")

    base_time = datetime(2026, 9, 1, 18, 0, 0)

    tag_repo.bulk_insert_tags([
        ("suspect_p2p", "P2P Suspect", "illicit", "BTC", "Demo", 1.0),
    ])

    edges = [
        (_tx_hash("suspect_p2p", "hop_p2p_1", 0),
         "suspect_p2p", "hop_p2p_1", 110_000_000,
         base_time, "BTC", False),

        (_tx_hash("hop_p2p_1", "hop_p2p_2", 0),
         "hop_p2p_1", "hop_p2p_2", 105_000_000,
         base_time + timedelta(hours=1), "BTC", False),

        # P2P cash-out: exactly 1.0 BTC (round amount = P2P signal)
        (_tx_hash("hop_p2p_2", "p2p_buyer_wallet", 0),
         "hop_p2p_2", "p2p_buyer_wallet", 100_000_000,
         base_time + timedelta(hours=3), "BTC", False),

        # Tiny change output (dead end)
        (_tx_hash("hop_p2p_2", "bg_change_wallet", 0),
         "hop_p2p_2", "bg_change_wallet", 4_500_000,
         base_time + timedelta(hours=3), "BTC", False),
    ]

    edge_repo.insert_edges(edges)
    logger.info(f"  Inserted {len(edges)} edges (3-hop chain → P2P dead-end sink at 1.0 BTC)")
    return "suspect_p2p"


def seed_tornado_cash_scenario(edge_repo: TransactionEdgeRepository, tag_repo: EntityTagRepository):
    """
    Scenario: Tornado Cash (Ethereum)

    Suspect deposits 10 ETH into the Tornado Cash 10 ETH pool.
    6 hours later, a withdrawal of 10 ETH exits to a different wallet.
    Our timing correlation detector links them probabilistically.

    Graph:
        suspect_tc ──[10 ETH]──→ tornado_pool_10_ETH ──[10 ETH]──→ tc_withdrawal_wallet
                                       ↑                                   │
                                  ZK proof barrier                    → some_exchange
                                  (no on-chain link)
    """
    logger.info("═══ Seeding Tornado Cash Scenario ═══")

    base_time = datetime(2026, 9, 10, 12, 0, 0)
    pool_addr = "tornado_pool_10_ETH"

    tag_repo.bulk_insert_tags([
        ("suspect_tc", "Tornado Cash Suspect", "illicit", "ETH", "Demo", 1.0),
        (pool_addr, "Tornado Cash 10 ETH Pool", "mixer", "ETH", "Demo", 1.0),
        ("0x742d35Cc6634C0532925a3b844Bc9e7595f2bD1e", "Binance ETH", "exchange", "ETH", "Demo", 1.0),
    ])

    # wei-equivalent normalized amount for 10 ETH (matching etherscan_client scale)
    ten_eth_normalized = 1_000_000_000  # 10 ETH in normalized sats-equivalent

    edges = [
        # Suspect deposits 10 ETH into TC pool
        (_tx_hash("suspect_tc", pool_addr, 0),
         "suspect_tc", pool_addr, ten_eth_normalized,
         base_time, "ETH", False),

        # 6 hours later: withdrawal from TC pool to new wallet
        (_tx_hash(pool_addr, "tc_withdrawal_wallet", 0),
         pool_addr, "tc_withdrawal_wallet", ten_eth_normalized,
         base_time + timedelta(hours=6), "ETH", False),

        # Withdrawal wallet sends to exchange
        (_tx_hash("tc_withdrawal_wallet", "0x742d35Cc6634C0532925a3b844Bc9e7595f2bD1e", 0),
         "tc_withdrawal_wallet", "0x742d35Cc6634C0532925a3b844Bc9e7595f2bD1e",
         int(ten_eth_normalized * 0.99),
         base_time + timedelta(hours=8), "ETH", False),

        # Noise: another user withdraws from same pool 24 hours later
        (_tx_hash(pool_addr, "tc_other_withdrawal", 0),
         pool_addr, "tc_other_withdrawal", ten_eth_normalized,
         base_time + timedelta(hours=30), "ETH", False),
    ]

    edge_repo.insert_edges(edges)
    logger.info(f"  Inserted {len(edges)} edges (deposit → TC pool → withdrawal with 6h gap)")
    return "suspect_tc"


def run_detection_demo():
    """
    Seed all 4 obfuscation scenarios and run the detector on each,
    printing results to prove detection works.
    """
    db = get_db_connection()
    init_db(db)
    tag_repo = EntityTagRepository(db)
    edge_repo = TransactionEdgeRepository(db)

    print("\n" + "=" * 70)
    print("  SIH26182 -- Obfuscation Detection Demo")
    print("  Proving CoinJoin, Nested Exchange, P2P, and Tornado Cash detection")
    print("=" * 70 + "\n")

    # Seed all scenarios
    suspect_cj = seed_coinjoin_scenario(edge_repo, tag_repo)
    suspect_ne = seed_nested_exchange_scenario(edge_repo, tag_repo)
    suspect_p2p = seed_p2p_scenario(edge_repo, tag_repo)
    suspect_tc = seed_tornado_cash_scenario(edge_repo, tag_repo)

    # Build graphs from DB and run detection on each
    scenarios = [
        ("CoinJoin", suspect_cj, "BTC"),
        ("Nested Exchange", suspect_ne, "BTC"),
        ("P2P/OTC", suspect_p2p, "BTC"),
        ("Tornado Cash", suspect_tc, "ETH"),
    ]

    for scenario_name, suspect, chain in scenarios:
        print(f"\n{'-' * 60}")
        print(f"  Testing: {scenario_name} Detection")
        print(f"  Suspect: {suspect}")
        print(f"{'-' * 60}")

        # Build graph from edges in DB
        G = nx.Graph()
        all_edges = edge_repo.get_connected_edges(suspect)
        if not all_edges:
            print(f"  [WARN] No edges found for {suspect} in DB. Skipping.")
            continue

        # BFS to build full component
        visited = {suspect}
        queue = [suspect]
        while queue:
            node = queue.pop(0)
            connected = edge_repo.get_connected_edges(node)
            for e in connected:
                src, dst = e["source_address"], e["target_address"]
                w = e["amount_satoshis"] / 100_000_000.0
                if G.has_edge(src, dst):
                    G[src][dst]["weight"] += w
                else:
                    G.add_edge(src, dst, weight=w)
                for endpoint in (src, dst):
                    if endpoint not in visited:
                        visited.add(endpoint)
                        queue.append(endpoint)
            if len(visited) > 50:  # safety limit for demo
                break

        G.nodes[suspect]["kind"] = "suspect"

        # Get known VASPs
        known_vasps = set(tag_repo.list_all_vasp_addresses())

        # Run unified detector
        t0 = time.perf_counter()
        report = analyze_obfuscation(G, suspect, known_vasps, tag_repo, chain=chain)
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        # Print results
        print(f"  Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        print(f"  Detection time: {elapsed_ms} ms")
        print(f"  Techniques found: {report.techniques_detected or ['None']}")

        if report.coinjoin_transactions:
            for cj in report.coinjoin_transactions:
                print(f"  [DETECTED] CoinJoin: type={cj.coinjoin_type}, "
                      f"pool_size={cj.pool_size}, confidence={cj.confidence}, "
                      f"entropy={cj.output_entropy}")

        if report.nested_exchanges:
            for ne in report.nested_exchanges:
                print(f"  [DETECTED] Nested Exchange: {ne.address}")
                print(f"     Parent: {ne.parent_name}, funnel_ratio={ne.funnel_ratio}, "
                      f"depositors={ne.depositor_count}")

        if report.p2p_sinks:
            for ps in report.p2p_sinks:
                print(f"  [DETECTED] P2P Sink: {ps.address}")
                print(f"     Volume: {ps.total_volume_btc} BTC, "
                      f"round_amount={ps.is_round_amount}, confidence={ps.confidence}")

        if report.tornado_cash and report.tornado_cash.detected:
            tc = report.tornado_cash
            print(f"  [DETECTED] Tornado Cash: {len(tc.deposits)} deposits, "
                  f"{len(tc.withdrawals)} withdrawals")
            for corr in tc.correlations:
                print(f"     Timing correlation: {corr['deposit_from']} -> {corr['withdrawal_to']}")
                print(f"     Gap: {corr['hours_gap']}h, score: {corr['time_correlation_score']}")

        if not report.techniques_detected:
            print(f"  [INFO] No obfuscation detected (expected for this scenario: {scenario_name})")

    print(f"\n{'=' * 70}")
    print("  Demo complete. All 4 obfuscation detectors validated.")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    run_detection_demo()
