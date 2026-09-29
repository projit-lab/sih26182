from datetime import datetime, timedelta
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx

from backend.config import DEFAULT_HOP_DEPTH, MAX_SUBGRAPH_NODES
from backend.database.db import get_db_connection
from backend.database.repositories import EntityTagRepository, TransactionEdgeRepository
from backend.ingestion.blockstream_client import BlockstreamClient
from backend.ingestion.etherscan_client import EtherscanClient

logger = logging.getLogger(__name__)


class SubgraphExtractor:
    """
    Downstream Subgraph Extractor:
    Traverses k-hop paths starting from a suspect wallet across BTC (UTXO)
    and ETH (EVM Account-based) networks, halts expansion at VASP boundaries,
    and compiles a weighted NetworkX Graph along with isolated candidate VASPs
    for AttributionEngine ($Lx = b$).
    """

    def __init__(
        self,
        db=None,
        tag_repo: EntityTagRepository | None = None,
        edge_repo: TransactionEdgeRepository | None = None,
        btc_client: BlockstreamClient | None = None,
        eth_client: EtherscanClient | None = None,
    ):
        self.db = db or get_db_connection()
        self.tag_repo = tag_repo or EntityTagRepository(self.db)
        self.edge_repo = edge_repo or TransactionEdgeRepository(self.db)
        self.btc_client = btc_client or BlockstreamClient(repo=self.edge_repo)
        self.eth_client = eth_client or EtherscanClient(repo=self.edge_repo)

    def extract_subgraph(
        self,
        suspect_address: str,
        max_depth: int = DEFAULT_HOP_DEPTH,
        chain: str = "BTC",
    ) -> Tuple[nx.Graph, List[str], Dict[str, dict], bool]:
        """
        Performs k-hop traversal:
        1. Uses Breadth-First Expansion across UTXO or EVM movements
        2. Prunes traversal at known VASP boundaries
        3. Builds weighted nx.Graph (weights = cumulative volume)
        4. Isolates candidate VASPs

        Returns:
            G (nx.Graph): Undirected weighted graph for AttributionEngine
            candidate_vasps (List[str]): Discovered VASP wallet addresses
            node_metadata (Dict[str, dict]): Map of address -> {role, entity, category}
            is_truncated (bool): True if the API or extraction truncated the history
        """
        known_vasps: Set[str] = set(self.tag_repo.list_all_vasp_addresses())
        is_eth = chain.upper() == "ETH" or suspect_address.startswith("0x")
        global_truncated = False

        visited_nodes: Set[str] = {suspect_address}
        # queue stores (address, depth, arrival_timestamp)
        queue: List[Tuple[str, int, Optional[datetime]]] = [(suspect_address, 0, None)]

        G = nx.Graph()
        G.add_node(suspect_address, kind="suspect")

        node_metadata: Dict[str, dict] = {
            suspect_address: {"role": "suspect", "label": suspect_address, "entity": "Suspect Target"}
        }

        from concurrent.futures import ThreadPoolExecutor

        fetch_client = self.eth_client if is_eth else self.btc_client

        while queue and len(visited_nodes) < MAX_SUBGRAPH_NODES:
            # Batch up to 4 nodes at the current depth to crawl concurrently (avoids public API rate-limits)
            current_depth = queue[0][1]
            batch: List[Tuple[str, int, Optional[datetime]]] = []
            while queue and queue[0][1] == current_depth and len(batch) < 4:
                addr, d, t_arr = queue.pop(0)
                if addr in known_vasps and addr != suspect_address:
                    continue
                if d >= max_depth:
                    continue
                batch.append((addr, d, t_arr))

            if not batch:
                continue

            def _fetch_node_edges(item: Tuple[str, int, Optional[datetime]]) -> Tuple[str, int, Optional[datetime], list, bool]:
                a, dep, t_a = item
                try:
                    edges, is_trunc = fetch_client.get_or_fetch_edges(a)
                    return a, dep, t_a, edges, is_trunc
                except Exception as ex:
                    logger.warning(f"Error fetching edges for {a}: {ex}")
                    return a, dep, t_a, [], False

            # Execute parallel concurrent fetch across all batch nodes
            if len(batch) == 1:
                batch_results = [_fetch_node_edges(batch[0])]
            else:
                with ThreadPoolExecutor(max_workers=len(batch)) as executor:
                    batch_results = list(executor.map(_fetch_node_edges, batch))

            for curr_addr, depth, t_arrival, edges, is_trunc in batch_results:
                if is_trunc:
                    global_truncated = True
                if not edges:
                    continue
                logger.info(f"Extractor fetched {len(edges)} edges for {curr_addr}")

                sorted_edges = sorted(edges, key=lambda e: e.amount_satoshis, reverse=True)

                for edge in sorted_edges[:50]:
                    src = edge.source_address
                    dst = edge.target_address
                    # Convert satoshis to BTC so conductances match engine contract scale
                    weight = max(1e-6, float(edge.amount_satoshis) / 100_000_000.0)

                    # Add to NetworkX graph (accumulate weights and satoshis if parallel flows exist)
                    if G.has_edge(src, dst):
                        G[src][dst]["weight"] += weight
                        G[src][dst]["amount_satoshis"] = G[src][dst].get("amount_satoshis", 0) + edge.amount_satoshis
                    else:
                        G.add_edge(src, dst, weight=weight, amount_satoshis=edge.amount_satoshis, tx_hash=edge.tx_hash)

                    # Classify node metadata for both endpoints
                    for endpoint in (src, dst):
                        if endpoint not in node_metadata:
                            if endpoint.upper() == "COINBASE":
                                node_metadata[endpoint] = {
                                    "role": "background",
                                    "label": "Coinbase (Mined)",
                                    "entity": "Coinbase Block Reward",
                                    "category": "mining",
                                }
                                continue

                            tag = self.tag_repo.get_tag(endpoint)
                            if tag:
                                role = "candidate_vasp" if tag["category"] in ("exchange", "custodial", "vasp") else tag["category"]
                                node_metadata[endpoint] = {
                                    "role": role,
                                    "label": tag["entity_name"],
                                    "entity": tag["entity_name"],
                                    "category": tag["category"],
                                }
                            elif "mixer" in endpoint.lower():
                                node_metadata[endpoint] = {"role": "mixer_hop", "label": endpoint, "entity": "Mixer Node"}
                            elif "hop" in endpoint.lower():
                                node_metadata[endpoint] = {"role": "hop", "label": endpoint, "entity": "Intermediary Hop"}
                            else:
                                node_metadata[endpoint] = {"role": "background", "label": endpoint, "entity": "Peer Wallet"}

                # High-degree super hub detection (unlisted mining pool, mixer hub, or exchange deposit cluster)
                # Halt deep expansion past massive non-suspect hubs to prevent graph explosion & noise
                is_super_hub = len(edges) >= 45 and curr_addr != suspect_address
                if is_super_hub:
                    if node_metadata.get(curr_addr, {}).get("role") == "background":
                        node_metadata[curr_addr]["entity"] = "High-Degree Cluster / Suspected Hub"
                        node_metadata[curr_addr]["role"] = "suspected_hub"
                    logger.info(f"Node {curr_addr} is a high-degree hub ({len(edges)} edges). Halting deeper branch expansion.")
                    continue

                # Filter candidate hops with Directional Temporal Causality (t_out >= t_in - 2h)
                candidate_hops: List[Tuple[Any, str]] = []
                for edge in sorted_edges:
                    next_hop = edge.target_address if edge.source_address == curr_addr else edge.source_address
                    if not next_hop or next_hop.upper() == "COINBASE":
                        continue
                    if next_hop in visited_nodes or next_hop in known_vasps:
                        continue

                    # Directional Temporal Filter:
                    # If funds are flowing downstream (edge.source_address == curr_addr),
                    # the outgoing transfer cannot have occurred prior to funds arriving at curr_addr.
                    # Leeway of 2 hours is granted to account for Bitcoin miner block timestamp drift.
                    if (
                        t_arrival is not None
                        and edge.timestamp is not None
                        and edge.source_address == curr_addr
                    ):
                        if edge.timestamp < t_arrival - timedelta(hours=2):
                            continue

                    candidate_hops.append((edge, next_hop))

                # Adaptive Cumulative Volume Beam Search:
                # Dynamically accumulate candidate branches until >= 85% of total candidate volume
                # is captured (bounded between MIN_BEAM=3 and MAX_BEAM=12).
                # This guarantees peel chains with dispersed equal-value splits are not prematurely pruned.
                total_candidate_vol = sum(e.amount_satoshis for e, _ in candidate_hops)
                accumulated_vol = 0
                hops_queued = 0
                min_beam = 3
                max_beam = 12
                target_ratio = 0.85

                for edge, next_hop in candidate_hops:
                    visited_nodes.add(next_hop)
                    queue.append((next_hop, depth + 1, edge.timestamp))
                    hops_queued += 1
                    accumulated_vol += edge.amount_satoshis

                    if hops_queued >= min_beam:
                        if hops_queued >= max_beam:
                            break
                        if total_candidate_vol > 0 and (accumulated_vol / total_candidate_vol) >= target_ratio:
                            break

        # Candidate VASP Isolation
        candidate_vasps = [n for n in G.nodes() if n in known_vasps and n != suspect_address]

        for n, meta in node_metadata.items():
            if n in G:
                G.nodes[n]["kind"] = meta["role"]

        logger.info(
            f"Extracted subgraph for '{suspect_address}' ({chain}): {G.number_of_nodes()} nodes, "
            f"{G.number_of_edges()} edges, {len(candidate_vasps)} candidate VASPs"
        )
        return G, candidate_vasps, node_metadata, global_truncated
