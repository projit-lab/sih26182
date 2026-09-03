from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from backend.models.common import CryptoAddress


class InvestigateRequest(BaseModel):
    suspect_address: CryptoAddress = Field(..., description="Target wallet address under investigation")
    chain: str = Field("BTC", description="Blockchain network (BTC, ETH, etc.)")
    depth_limit: int = Field(4, ge=1, le=10, description="Maximum traversal depth (k-hop)")
    candidate_vasps: Optional[List[str]] = Field(
        None,
        description="Optional explicit candidate VASP address list. If omitted, discovered VASPs in subgraph are used.",
    )


class RankedVaspItem(BaseModel):
    vasp_name: str = Field(..., description="Entity name of the VASP (e.g., Binance, WazirX)")
    candidate_address: str = Field(..., description="Wallet address associated with the VASP")
    effective_resistance: float = Field(..., description="Computed circuit effective resistance (lower = stronger link)")
    confidence_score: float = Field(..., description="Normalized attribution probability [0.0 - 1.0]")


class GraphSummary(BaseModel):
    nodes_analyzed: int
    edges_analyzed: int
    compute_time_ms: float
    solver_method: str = "effective_resistance"


class InvestigateResponse(BaseModel):
    suspect_address: str
    ranked_vasps: List[RankedVaspItem]
    graph_summary: GraphSummary


# --- Backwards compatibility with frozen ENGINE_CONTRACT.md ---
class AttributionRequest(BaseModel):
    suspect_wallet: str
    candidate_vasps: List[str]


class AttributionResponse(BaseModel):
    suspect: str
    ranked_candidates: List[str]
    scores: Dict[str, float]
    method: str = "effective_resistance"
