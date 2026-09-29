import logging
from fastapi import APIRouter, HTTPException, Query

from backend.models.common import validate_crypto_address
from backend.models.graph import SubgraphResponse
from backend.services.graph_service import GraphService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/graph", tags=["Graph Visualizations"])


@router.get("/subgraph/{address}", response_model=SubgraphResponse)
def get_address_subgraph(
    address: str,
    depth: int = Query(3, ge=1, le=10, description="Traversal depth limit (hops)"),
    chain: str = Query("BTC", description="Blockchain network (BTC, ETH)"),
):
    """
    Returns nodes and edges formatted for Cytoscape.js or D3.js frontend visualization,
    including role classifications (suspect, mixer_hop, candidate_vasp, background).
    """
    try:
        sanitized_addr = validate_crypto_address(address)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        service = GraphService()
        subgraph = service.get_cytoscape_subgraph(
            suspect_address=sanitized_addr, max_depth=depth, chain=chain
        )
        logger.info(
            f"API Subgraph for '{sanitized_addr}': {len(subgraph.nodes)} nodes, {len(subgraph.edges)} edges"
        )
        if not subgraph.nodes:
            raise HTTPException(
                status_code=404,
                detail=f"No transaction subgraph found for address '{address}'",
            )
        return subgraph
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error extracting subgraph")
        raise HTTPException(status_code=500, detail=f"Failed to extract subgraph: {str(e)}")
