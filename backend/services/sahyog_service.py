import hashlib
import uuid
from datetime import datetime
from typing import Optional

from backend.database.repositories import SahyogRepository
from backend.models.sahyog import SahyogDispatchRequest, SahyogDispatchResponse


class SahyogService:
    """
    Mock Indian Law Enforcement / SAHYOG Portal Dispatcher.
    Simulates statutory Section 91 CrPC lawful freeze / KYC requests to VASPs.
    """

    def __init__(self, repo: Optional[SahyogRepository] = None):
        self.repo = repo or SahyogRepository()

    def dispatch_notice(self, req: SahyogDispatchRequest) -> SahyogDispatchResponse:
        # Generate official acknowledgment token
        unique_suffix = uuid.uuid4().hex[:6].upper()
        ack_token = f"SAHYOG-ACK-2026-{unique_suffix}"
        now_str = datetime.utcnow().isoformat() + "Z"

        # Cryptographic audit hash representing tamper-proof dispatch record
        payload_raw = (
            f"{req.case_id}:{req.suspect_address}:{req.target_vasp}:{req.action}:{now_str}"
        )
        dispatch_hash = hashlib.sha256(payload_raw.encode("utf-8")).hexdigest()

        # Save to database
        self.repo.create_dispatch(
            ack_token=ack_token,
            case_id=req.case_id,
            suspect_address=req.suspect_address,
            target_vasp=req.target_vasp,
            action=req.action,
            officer_name=req.officer_name,
            jurisdiction=req.jurisdiction,
            law_section=req.law_section,
            dispatch_hash=dispatch_hash,
            status="SUBMITTED",
        )

        vasp_slug = req.target_vasp.lower().replace(" ", "")
        compliance_url = f"https://compliance.{vasp_slug}.in/le-portal/v2/dispatches/{ack_token}"

        return SahyogDispatchResponse(
            ack_token=ack_token,
            case_id=req.case_id,
            suspect_address=req.suspect_address,
            target_vasp=req.target_vasp,
            action=req.action,
            status="SUBMITTED",
            timestamp=now_str,
            dispatch_hash=dispatch_hash,
            vasp_compliance_portal=compliance_url,
        )

    def get_dispatch_status(self, ack_token: str) -> Optional[dict]:
        return self.repo.get_dispatch(ack_token)
