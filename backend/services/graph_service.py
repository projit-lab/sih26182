import logging
from typing import Optional

from backend.ingestion.extractor import SubgraphExtractor
from backend.models.graph import (
    CytoscapeEdge,
    CytoscapeEdgeData,
    CytoscapeNode,
    CytoscapeNodeData,
    SubgraphResponse,
)

logger = logging.getLogger(__name__)


class GraphService:
    """
    Translates extracted network graphs into Cytoscape.js and D3.js schemas
    for visualization in the frontend.
    """

    def __init__(self, extractor: Optional[SubgraphExtractor] = None):
        self.extractor = extractor or SubgraphExtractor()

    def get_cytoscape_subgraph(
        self, suspect_address: str, max_depth: int = 3, chain: str = "BTC"
    ) -> SubgraphResponse:
        graph, candidate_vasps, metadata, is_truncated = self.extractor.extract_subgraph(
            suspect_address=suspect_address, max_depth=max_depth, chain=chain
        )

        nodes: list[CytoscapeNode] = []
        for node_id in graph.nodes():
            meta = metadata.get(node_id, {})
            role = meta.get("role", "background")
            label = meta.get("label", node_id)
            entity = meta.get("entity")
            category = meta.get("category")

            nodes.append(
                CytoscapeNode(
                    data=CytoscapeNodeData(
                        id=node_id,
                        label=label,
                        role=role,
                        entity=entity,
                        category=category,
                    )
                )
            )

        edges: list[CytoscapeEdge] = []
        for u, v, data in graph.edges(data=True):
            weight = float(data.get("weight", 1.0))
            raw_sats = data.get("amount_satoshis")
            if raw_sats is not None:
                amount_sats = int(raw_sats)
            else:
                amount_sats = int(weight) if weight > 1000 else int(round(weight * 100_000_000))

            edge_id = f"{u}->{v}"
            edges.append(
                CytoscapeEdge(
                    data=CytoscapeEdgeData(
                        id=edge_id,
                        source=u,
                        target=v,
                        weight=weight,
                        amount_satoshis=amount_sats,
                        tx_hash=data.get("tx_hash"),
                    )
                )
            )

        return SubgraphResponse(
            suspect_address=suspect_address,
            nodes=nodes,
            edges=edges,
            stats={
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "candidate_vasps_count": len(candidate_vasps),
                "depth_explored": max_depth,
            },
        )
