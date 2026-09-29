import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "SIH26182 Backend & Ingestion Layer"


def test_serve_ui(client):
    response = client.get("/app")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Cytoscape" in response.text or "cy" in response.text


def test_investigate_scenario_0(client):
    payload = {
        "suspect_address": "suspect_042",
        "depth_limit": 3,
        "chain": "BTC"
    }
    response = client.post("/api/v1/investigate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["suspect_address"] == "suspect_042"
    assert len(data["ranked_vasps"]) > 0
    # Top VASP should be VASP_true (Binance)
    assert data["ranked_vasps"][0]["vasp_name"] == "Binance"
    assert "graph_summary" in data
    assert data["graph_summary"]["nodes_analyzed"] > 0
    assert "truncated" in data["graph_summary"]
    assert "obfuscation_report" in data


def test_investigate_silkroad(client):
    payload = {
        "case_id": "silkroad",
        "suspect_address": "1F1tAaz5x1HUXrCNLbtMDqcw6o5GNn4xqX",
        "depth_limit": 2,
        "chain": "BTC"
    }
    response = client.post("/api/v1/investigate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["suspect_address"] == "1F1tAaz5x1HUXrCNLbtMDqcw6o5GNn4xqX"
    assert len(data["ranked_vasps"]) > 0
    assert "Coinbase" in data["ranked_vasps"][0]["vasp_name"]


def test_sahyog_dispatch(client):
    payload = {
        "case_id": "TEST-CASE-001",
        "suspect_address": "1F1tAaz5x1HUXrCNLbtMDqcw6o5GNn4xqX",
        "target_vasp": "Coinbase Prime Institutional Vault",
        "action": "FREEZE_REQUEST",
        "officer_name": "IO Cyber Cell",
        "jurisdiction": "Cyber Crime Division",
        "law_section": "Section 91 CrPC"
    }
    response = client.post("/api/v1/sahyog/dispatch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "ack_token" in data
    assert "dispatch_hash" in data
