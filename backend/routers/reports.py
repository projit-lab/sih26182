import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.services.report_service import ReportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reports", tags=["Forensic Reports"])
_report_service = ReportService()


@router.get("/project-overview/export")
def export_project_overview_report():
    """
    Exports a comprehensive multi-page PDF report covering the full SIH26182 implementation:
    circuit theory mathematical breakthrough (Lx = b), multi-tier ingestion, bounded subgraph extraction,
    benchmarks, mock SAHYOG integration (simulated), and architecture specs.
    """
    try:
        import io
        from backend.services.project_report_generator import build_project_implementation_pdf
        buf = io.BytesIO()
        build_project_implementation_pdf(buf)
        pdf_bytes = buf.getvalue()
        
        # Also persist directly to project root for local access
        try:
            from pathlib import Path
            root_dir = Path(__file__).resolve().parent.parent.parent
            with open(root_dir / "SIH26182_Project_Implementation_Report.pdf", "wb") as f:
                f.write(pdf_bytes)
        except Exception as write_err:
            logger.warning(f"Could not persist PDF copy to disk: {write_err}")

        buf.seek(0)
        filename = "SIH26182_Project_Implementation_Report.pdf"
        return StreamingResponse(
            buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        logger.exception("Failed to export project overview PDF report")
        raise HTTPException(status_code=500, detail=f"Project Report Generation Error: {str(e)}")


@router.get("/backend-implementation/export")
def export_backend_implementation_report():
    """
    Exports a comprehensive PDF report covering the full backend implementation,
    function-by-function specifications, code snippets, and grounded Laplacian architecture.
    """
    try:
        import io
        from pathlib import Path
        from generate_backend_pdf import build_backend_report_pdf

        root_dir = Path(__file__).resolve().parent.parent.parent
        pdf_path = root_dir / "SIH26182_Backend_Implementation_Report.pdf"
        build_backend_report_pdf(pdf_path)

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        buf = io.BytesIO(pdf_bytes)
        filename = "SIH26182_Backend_Implementation_Report.pdf"
        return StreamingResponse(
            buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        logger.exception("Failed to export backend implementation PDF report")
        raise HTTPException(status_code=500, detail=f"Backend Report Generation Error: {str(e)}")


@router.get("/{case_id}/export")
def export_case_report(case_id: str):
    """
    Exports a prototype investigator lead report (PDF) featuring circuit theory
    mathematical attribution tables and top-1 VASP identification.
    This is NOT a court-admissible document and NOT certified under any evidence act.
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
