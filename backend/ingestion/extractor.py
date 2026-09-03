import logging
from typing import Dict, List, Set, Tuple
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
    ) -> Tuple[nx.Graph, List[str], Dict[str, dict]]:
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
        """
        known_vasps: Set[str] = set(self.tag_repo.list_all_vasp_addresses())
        is_eth = chain.upper() == "ETH" or suspect_address.startswith("0x")

        visited_nodes: Set[str] = {suspect_address}
        queue: List[Tuple[str, int]] = [(suspect_address, 0)]

        G = nx.Graph()
        G.add_node(suspect_address, kind="suspect")

        node_metadata: Dict[str, dict] = {
            suspect_address: {"role": "suspect", "label": suspect_address, "entity": "Suspect Target"}
        }

        while queue and len(visited_nodes) < MAX_SUBGRAPH_NODES:
            curr_addr, depth = queue.pop(0)

            # Stop expansion along a path once a recognized VASP node is reached
            if curr_addr in known_vasps and curr_addr != suspect_address:
                continue

            if depth >= max_depth:
                continue

            # Fetch outgoing edges (from DB cache, Blockstream/Mempool, or Etherscan)
            if is_eth:
                edges = self.eth_client.get_or_fetch_edges(curr_addr)
            else:
                edges = self.btc_client.get_or_fetch_edges(curr_addr)

            for edge in edges:
                src = edge.source_address
                dst = edge.target_address
                # Convert satoshis to BTC (or normalized units) so conductances match engine contract scale
                # 1 BTC = 100,000,000 sats; prevents effective resistance underflowing to 0.0000
                weight = max(1e-6, float(edge.amount_satoshis) / 100_000_000.0)

                # Add to NetworkX graph (accumulate weights if parallel flows exist)
                if G.has_edge(src, dst):
                    G[src][dst]["weight"] += weight
                else:
                    G.add_edge(src, dst, weight=weight)

                # Classify node metadata
                if dst not in node_metadata:
                    tag = self.tag_repo.get_tag(dst)
                    if tag:
                        role = "candidate_vasp" if tag["category"] in ("exchange", "custodial", "vasp") else tag["category"]
                        node_metadata[dst] = {
                            "role": role,
                            "label": tag["entity_name"],
                            "entity": tag["entity_name"],
                            "category": tag["category"],
                        }
                    elif "mixer" in dst.lower():
                        node_metadata[dst] = {"role": "mixer_hop", "label": dst, "entity": "Mixer Node"}
                    elif "hop" in dst.lower():
                        node_metadata[dst] = {"role": "hop", "label": dst, "entity": "Intermediary Hop"}
                    else:
                        node_metadata[dst] = {"role": "background", "label": dst, "entity": "Peer Wallet"}

                if dst not in visited_nodes:
                    visited_nodes.add(dst)
                    queue.append((dst, depth + 1))

        # Candidate VASP Isolation
        candidate_vasps = [n for n in G.nodes() if n in known_vasps and n != suspect_address]

        for n, meta in node_metadata.items():
            if n in G:
                G.nodes[n]["kind"] = meta["role"]

        logger.info(
            f"Extracted subgraph for '{suspect_address}' ({chain}): {G.number_of_nodes()} nodes, "
            f"{G.number_of_edges()} edges, {len(candidate_vasps)} candidate VASPs"
        )
        return G, candidate_vasps, node_metadata
