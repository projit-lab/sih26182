from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.models.common import CryptoAddress


class InvestigateRequest(BaseModel):
    suspect_address: CryptoAddress = Field(..., description="Target wallet address under investigation")
    chain: str = Field("BTC", description="Blockchain network (BTC, ETH, etc.)")
    depth_limit: int = Field(4, ge=1, le=10, description="Maximum traversal depth (k-hop)")
    case_id: Optional[str] = Field(None, description="Optional case ID to load pre-verified cases (e.g. 'silkroad')")
    candidate_vasps: Optional[List[str]] = Field(
        None,
        description="Optional explicit candidate VASP address list. If omitted, discovered VASPs in subgraph are used.",
    )


class RankedVaspItem(BaseModel):
    vasp_name: str = Field(..., description="Entity name of the VASP (e.g., Binance, WazirX)")
    candidate_address: str = Field(..., description="Wallet address associated with the VASP")
    effective_resistance: float = Field(..., description="Computed circuit effective resistance (lower = stronger link)")
    raw_effective_resistance: float = Field(..., description="Uncorrected effective resistance")
    score: float = Field(..., description="Ranked score")
    confidence_score: Optional[float] = Field(None, description="Deprecated. Normalized attribution probability")


class GraphSummary(BaseModel):
    nodes_analyzed: int
    edges_analyzed: int
    compute_time_ms: float
    solver_method: str = "effective_resistance"
    truncated: bool = Field(
        False,
        description="True if the subgraph was truncated by MAX_SUBGRAPH_NODES cap",
    )


class InvestigateResponse(BaseModel):
    case_id: Optional[str] = Field(None, description="Unique case reference for audit and PDF reporting")
    suspect_address: str
    ranked_vasps: List[RankedVaspItem]
    graph_summary: GraphSummary
    obfuscation_report: Optional[Dict[str, Any]] = Field(
        None,
        description="Detected obfuscation techniques: CoinJoin, nested exchanges, P2P sinks, Tornado Cash",
    )
    separation_ratio: Optional[float] = None
    degree_corrected: bool = False
    null_test: Optional[Any] = None
    unreachable_vasps: List[Dict[str, str]] = Field(default_factory=list)
    data_source: str = "live/cached crawl"


# --- Backwards compatibility with frozen ENGINE_CONTRACT.md ---
class AttributionRequest(BaseModel):
    suspect_wallet: str
    candidate_vasps: List[str]


class AttributionResponse(BaseModel):
    suspect: str
    ranked_candidates: List[str]
    scores: Dict[str, float]
    method: str = "effective_resistance"
