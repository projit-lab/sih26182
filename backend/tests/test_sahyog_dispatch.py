from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_sahyog_dispatch_and_retrieve():
    payload = {
        "case_id": "CASE-TEST-8841",
        "suspect_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        "target_vasp": "Binance",
        "action": "FREEZE_REQUEST",
        "officer_name": "Inspector Vikram",
        "jurisdiction": "Special Cell, Delhi Police",
        "law_section": "Section 91 CrPC",
    }
    # Dispatch notice
    resp = client.post("/api/v1/sahyog/dispatch", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["ack_token"].startswith("MOCK-SAHYOG-ACK-2026-")
    assert data["status"] == "SIMULATED"
    assert data["simulated"] is True
    assert "dispatch_hash" in data
    assert len(data["dispatch_hash"]) == 64  # SHA256 hex string

    # Query notice details
    ack_token = data["ack_token"]
    get_resp = client.get(f"/api/v1/sahyog/{ack_token}")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["ack_token"] == ack_token
    assert get_data["case_id"] == "CASE-TEST-8841"
    assert get_data["target_vasp"] == "Binance"


def test_sahyog_invalid_token_returns_404():
    resp = client.get("/api/v1/sahyog/SAHYOG-NONEXISTENT")
    assert resp.status_code == 404
