from fastapi.testclient import TestClient
from backend.main import app
from backend.database.db import get_db_connection, init_db
from backend.ingestion.seed_demo import seed_database

client = TestClient(app)


def setup_module():
    # Ensure database is initialized and seeded before running API tests
    db = get_db_connection()
    init_db(db)
    seed_database(num_cases=5)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_investigate_seeded_case():
    payload = {
        "suspect_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        "chain": "BTC",
        "depth_limit": 4,
    }
    response = client.post("/api/v1/investigate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["suspect_address"] == "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    assert "case_id" in data and data["case_id"].startswith("CASE-")
    assert "ranked_vasps" in data
    assert len(data["ranked_vasps"]) > 0

    top_vasp = data["ranked_vasps"][0]
    assert "vasp_name" in top_vasp
    assert "effective_resistance" in top_vasp
    assert "confidence_score" in top_vasp
    assert top_vasp["effective_resistance"] > 0.0
    assert top_vasp["confidence_score"] > 0.0

    assert "graph_summary" in data
    assert data["graph_summary"]["nodes_analyzed"] > 1
    assert data["graph_summary"]["compute_time_ms"] >= 0


def test_investigate_unknown_wallet_returns_404():
    payload = {
        "suspect_address": "demo_UnknownWalletThatDoesNotExist9999x",
        "chain": "BTC",
        "depth_limit": 3,
    }
    response = client.post("/api/v1/investigate", json=payload)
    assert response.status_code == 404


def test_frozen_contract_attribute_endpoint():
    payload = {
        "suspect_wallet": "suspect_042",
        "candidate_vasps": ["VASP_true", "VASP_decoy"],
    }
    response = client.post("/attribute", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["suspect"] == "suspect_042"
    assert "ranked_candidates" in data
    assert data["ranked_candidates"][0] == "VASP_true"
    assert "scores" in data
    assert data["method"] == "effective_resistance"


def test_graph_subgraph_endpoint():
    response = client.get("/api/v1/graph/subgraph/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa?depth=2")
    assert response.status_code == 200
    data = response.json()

    assert data["suspect_address"] == "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    assert len(data["nodes"]) > 0
    assert len(data["edges"]) > 0
    assert "role" in data["nodes"][0]["data"]
