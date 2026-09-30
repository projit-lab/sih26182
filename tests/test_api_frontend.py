import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_api_cases_shape():
    with TestClient(app) as c:
        resp = c.get("/cases")
        assert resp.status_code == 200
        data = resp.json()
        assert "silkroad" in data
        sr = data["silkroad"]
        assert "suspect" in sr
        assert "nodes" in sr
        assert "edges" in sr
        assert "n_components" in sr
        assert "suspect_component_size" in sr
        assert "truncated" in sr

def test_api_attribute_response_and_cors():
    with TestClient(app) as c:
        headers = {
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        }
        options_resp = c.options("/attribute", headers=headers)
        assert options_resp.status_code == 200
        assert options_resp.headers.get("access-control-allow-origin") == "http://localhost:5173"

        post_resp = c.post("/attribute", json={"case_id": "silkroad"})
        assert post_resp.status_code == 200
        data = post_resp.json()
        
        # Check hop_depths and dijkstra_comparison
        assert "hop_depths" in data
        assert "dijkstra_comparison" in data
        assert "winner" in data["dijkstra_comparison"]
        
        # Check graph_elements node count matches suspect_component_size
        cases_resp = c.get("/cases")
        comp_size = cases_resp.json()["silkroad"]["suspect_component_size"]
        
        assert "graph_elements" in data
        assert len(data["graph_elements"]["nodes"]) == comp_size
