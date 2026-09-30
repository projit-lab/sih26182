import logging
from fastapi import APIRouter, HTTPException

from backend.models.sahyog import SahyogDispatchRequest, SahyogDispatchResponse
from backend.services.sahyog_service import SahyogService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sahyog", tags=["SAHYOG Lawful Dispatcher"])
_sahyog_service = SahyogService()


@router.post("/dispatch", response_model=SahyogDispatchResponse)
def dispatch_lawful_notice(req: SahyogDispatchRequest):
    """
    Simulates formal Section 91 CrPC lawful freeze / KYC disclosure dispatch
    to destination VASP via mock Indian Government SAHYOG platform.
    Returns official government acknowledgment token.
    """
    try:
        return _sahyog_service.dispatch_notice(req)
    except Exception as e:
        logger.exception("Failed to dispatch SAHYOG notice")
        raise HTTPException(status_code=500, detail=f"SAHYOG Dispatch Error: {str(e)}")


@router.get("/{ack_token}")
def get_dispatch_details(ack_token: str):
    """
    Retrieve status and details of a previously submitted SAHYOG dispatch notice.
    """
    record = _sahyog_service.get_dispatch_status(ack_token)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Acknowledgment token '{ack_token}' not found in SAHYOG registry.",
        )
    return record
