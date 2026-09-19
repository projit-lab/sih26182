from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ReportMetadata(BaseModel):
    case_id: str
    suspect_address: str
    investigating_agency: str = "Cyber Crime Unit / Law Enforcement"
    generated_at: str
    top_attributed_vasp: str
    confidence_score: float
    effective_resistance: float
    nodes_analyzed: int
    edges_analyzed: int
    sahyog_token: Optional[str] = None


class ReportExportResponse(BaseModel):
    case_id: str
    filename: str
    content_type: str = "application/pdf"
    file_size_bytes: int
