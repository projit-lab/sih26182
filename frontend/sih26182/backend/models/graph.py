from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CytoscapeNodeData(BaseModel):
    id: str
    label: str
    role: str = Field(
        "background",
        description="Node classification: 'suspect', 'mixer_hop', 'candidate_vasp', 'hop', 'background'",
    )
    entity: Optional[str] = None
    category: Optional[str] = None


class CytoscapeNode(BaseModel):
    data: CytoscapeNodeData


class CytoscapeEdgeData(BaseModel):
    id: str
    source: str
    target: str
    weight: float
    amount_satoshis: int
    tx_hash: Optional[str] = None


class CytoscapeEdge(BaseModel):
    data: CytoscapeEdgeData


class SubgraphResponse(BaseModel):
    suspect_address: str
    nodes: List[CytoscapeNode]
    edges: List[CytoscapeEdge]
    stats: Dict[str, Any] = Field(default_factory=dict)
