from typing import Optional
from pydantic import BaseModel, Field

from backend.models.common import CryptoAddress


class SahyogDispatchRequest(BaseModel):
    case_id: str = Field(..., description="Unique investigation incident identifier")
    suspect_address: CryptoAddress = Field(..., description="Target wallet being traced")
    target_vasp: str = Field(..., description="VASP entity name (e.g., Binance, WazirX)")
    action: str = Field(
        "FREEZE_REQUEST",
        description="Lawful action requested: FREEZE_REQUEST, KYC_DISCLOSURE, TRANSACTION_LOGS",
    )
    officer_name: str = Field("Insp. R. Sharma", description="Investigating Officer name")
    jurisdiction: str = Field("Cyber Crime Unit, Delhi Police", description="Law enforcement jurisdiction")
    law_section: str = Field("Section 91 CrPC", description="Statutory authority section")


class SahyogDispatchResponse(BaseModel):
    ack_token: str = Field(..., description="MOCK acknowledgment token (simulated, no real SAHYOG call)")
    case_id: str
    suspect_address: str
    target_vasp: str
    action: str
    status: str = "SIMULATED"
    timestamp: str
    dispatch_hash: str = Field(..., description="Demo checksum of request parameters (not a certification)")
    vasp_compliance_portal: str
    simulated: bool = True
