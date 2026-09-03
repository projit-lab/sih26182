import logging
from fastapi import APIRouter, HTTPException

from backend.models.attribution import (
    AttributionRequest,
    AttributionResponse,
    InvestigateRequest,
    InvestigateResponse,
)
from backend.services.attribution_service import AttributionService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Attribution & Investigation"])


@router.post("/api/v1/investigate", response_model=InvestigateResponse)
def investigate_wallet(req: InvestigateRequest):
    """
    Primary General CSE investigation endpoint:
    1. Traverses k-hop outgoing UTXO movements from suspect address
    2. Dynamically isolates candidate VASP nodes
    3. Solves grounded Laplacian matrix (Lx = b) via circuit theory
    4. Returns ranked VASPs, effective resistance, and normalized confidence scores
    """
    try:
        service = AttributionService()
        return service.investigate(req)
    except ValueError as e:
        err_msg = str(e)
        if "not found in" in err_msg or "no transaction history" in err_msg:
            raise HTTPException(status_code=404, detail=err_msg)
        raise HTTPException(status_code=400, detail=err_msg)
    except Exception as e:
        logger.exception("Unexpected error during investigation")
        raise HTTPException(status_code=500, detail=f"Internal attribution solver error: {str(e)}")


# --- Backwards compatibility route matching docs/ENGINE_CONTRACT.md ---
@router.post("/attribute", response_model=AttributionResponse)
def attribute_frozen_contract(req: AttributionRequest):
    """
    Legacy frozen contract endpoint:
    Takes { suspect_wallet, candidate_vasps } and returns raw effective resistance scores.
    """
    if not req.candidate_vasps:
        raise HTTPException(status_code=400, detail="candidate_vasps list cannot be empty")

    inv_req = InvestigateRequest(
        suspect_address=req.suspect_wallet,
        candidate_vasps=req.candidate_vasps,
        depth_limit=5,
    )
    try:
        resp = _service.investigate(inv_req)
        scores = {item.candidate_address: item.effective_resistance for item in resp.ranked_vasps}
        ranked = [item.candidate_address for item in resp.ranked_vasps]
        return AttributionResponse(
            suspect=resp.suspect_address,
            ranked_candidates=ranked,
            scores=scores,
            method="effective_resistance",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=f"Suspect wallet '{req.suspect_wallet}' not found in current graph")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
