import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.services.report_service import ReportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reports", tags=["Forensic Reports"])
_report_service = ReportService()


@router.get("/{case_id}/export")
def export_case_report(case_id: str):
    """
    Exports a court-admissible LEA-style forensic incident report (PDF)
    featuring circuit theory mathematical attribution tables,
    top-1 VASP identification, and Section 65B Indian Evidence Act certification.
    """
    try:
        pdf_buffer = _report_service.generate_pdf_report(case_id)
        filename = f"Forensic_Report_{case_id}.pdf"
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Failed to export PDF report")
        raise HTTPException(status_code=500, detail=f"Report Generation Error: {str(e)}")
