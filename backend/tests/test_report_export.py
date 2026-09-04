from fastapi.testclient import TestClient
from backend.main import app
from backend.database.db import get_db_connection
from backend.database.repositories import CaseRepository

client = TestClient(app)


def test_export_pdf_report():
    # Save a mock case in DB first
    db = get_db_connection()
    repo = CaseRepository(db)
    mock_case_id = "CASE-REPORT-TEST-100"
    repo.save_case(
        case_id=mock_case_id,
        suspect_address="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        top_vasp="Binance",
        confidence=0.88,
        results_data={
            "suspect_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "ranked_vasps": [
                {
                    "vasp_name": "Binance",
                    "candidate_address": "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s",
                    "effective_resistance": 0.142,
                    "confidence_score": 0.88,
                }
            ],
            "graph_summary": {
                "nodes_analyzed": 1420,
                "edges_analyzed": 3890,
                "compute_time_ms": 4.2,
                "solver_method": "effective_resistance",
            },
        },
    )

    # Request PDF export
    resp = client.get(f"/api/v1/reports/{mock_case_id}/export")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")

    # Request PDF export by suspect address fallback
    resp_addr = client.get("/api/v1/reports/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa/export")
    assert resp_addr.status_code == 200
    assert resp_addr.headers["content-type"] == "application/pdf"


def test_export_unknown_case_returns_404():
    resp = client.get("/api/v1/reports/CASE-NONEXISTENT/export")
    assert resp.status_code == 404
