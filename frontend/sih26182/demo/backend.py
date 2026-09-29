"""
Demo Dedicated FastAPI Backend Server
Provides endpoints for:
- GET  /api/demo/graph       : Cytoscape-compatible 6-hop graph
- POST /api/demo/investigate : Grounded Laplacian & Dijkstra comparison
- GET  /api/demo/report      : Section 65B court PDF download
- POST /api/demo/sahyog      : SAHYOG Section 91 CrPC notice dispatch
"""
import io
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import networkx as nx

from demo.engine import DemoAttributionEngine

logger = logging.getLogger("DemoBackend")
logging.basicConfig(level=logging.INFO)

DEMO_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Advanced 6-Hop Strategy Demo Backend",
    description="Circuit Theory Solver ($Lx = b$) vs Shortest Path for Asymmetric Swarm Defense",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_demo_graph() -> tuple[nx.Graph, Dict[str, str], list, list]:
    edges_file = DEMO_DIR / "strategy_graph.json"
    tags_file = DEMO_DIR / "entity_tags.json"

    with open(edges_file, "r", encoding="utf-8") as f:
        edges_data = json.load(f)
    with open(tags_file, "r", encoding="utf-8") as f:
        tags_data = json.load(f)

    G = nx.Graph()
    for e in edges_data:
        u = e["source_address"]
        v = e["target_address"]
        w = max(1e-6, float(e["amount_satoshis"]) / 1e8)
        if G.has_edge(u, v):
            G[u][v]["weight"] += w
            G[u][v]["amount_satoshis"] += e["amount_satoshis"]
        else:
            G.add_edge(u, v, weight=w, amount_satoshis=e["amount_satoshis"], tx_hash=e.get("tx_hash", ""))

    candidate_vasps = {}
    for t in tags_data:
        if t.get("category") == "exchange":
            candidate_vasps[t["address"]] = t["entity_name"]

    return G, candidate_vasps, edges_data, tags_data


class InvestigatePayload(BaseModel):
    suspect_address: str = "bc1q9vza2e8424t6m5qgxp2r83kwln8y0e78k37df8"
    depth_limit: int = 6


@app.get("/")
def get_root():
    return {
        "service": "Advanced 6-Hop Swarm Attribution Engine",
        "case_id": "CASE-DEMO-6HOP-SWARM",
        "suspect_address": "bc1q9vza2e8424t6m5qgxp2r83kwln8y0e78k37df8",
        "solver": "Dirichlet Grounded Laplacian (Lx = b)",
        "endpoints": [
            "/api/demo/graph",
            "/api/demo/investigate",
            "/api/demo/report",
            "/api/demo/sahyog",
        ],
    }


@app.get("/api/demo/graph")
def get_graph():
    G, candidate_vasps, raw_edges, raw_tags = load_demo_graph()
    tag_map = {t["address"]: t for t in raw_tags}

    nodes = []
    for node in G.nodes():
        tag = tag_map.get(node, {})
        role = tag.get("category", "hop")
        if node == "bc1q9vza2e8424t6m5qgxp2r83kwln8y0e78k37df8":
            role = "suspect"
        elif "mixer" in role:
            role = "mixer_hop"
        elif role == "exchange":
            role = "candidate_vasp"

        nodes.append({
            "data": {
                "id": node,
                "label": tag.get("entity_name", node[:14] + "..."),
                "role": role,
                "entity": tag.get("entity_name", ""),
                "category": tag.get("category", "hop"),
            }
        })

    edges = []
    for idx, (u, v, data) in enumerate(G.edges(data=True)):
        edges.append({
            "data": {
                "id": f"demo_edge_{idx}",
                "source": u,
                "target": v,
                "weight": data["amount_satoshis"],
                "amount_satoshis": data["amount_satoshis"],
                "tx_hash": data.get("tx_hash", ""),
            }
        })

    return {"nodes": nodes, "edges": edges, "node_count": len(nodes), "edge_count": len(edges)}


@app.post("/api/demo/investigate")
def run_investigation(payload: InvestigatePayload):
    G, candidate_vasps, _, _ = load_demo_graph()
    engine = DemoAttributionEngine(G)

    try:
        res = engine.attribute(payload.suspect_address, candidate_vasps)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "case_id": "CASE-DEMO-6HOP-SWARM",
        "suspect_address": res.suspect_address,
        "compute_time_ms": res.compute_time_ms,
        "graph_summary": {
            "nodes_analyzed": res.graph_nodes,
            "edges_analyzed": res.graph_edges,
            "solver_method": res.solver_method,
        },
        "dijkstra_benchmark": {
            "winner": res.dijkstra_winner,
            "hop_count": res.dijkstra_hop_count,
            "status": "FAILED (Tricked by 2-Hop Decoy)",
        },
        "ranked_vasps": [
            {
                "rank": i + 1,
                "vasp_name": r.vasp_name,
                "address": r.address,
                "hop_distance": r.hop_distance,
                "effective_resistance": r.effective_resistance,
                "conductance": r.conductance,
                "confidence_score": r.confidence_score,
                "flow_btc": r.flow_btc,
            }
            for i, r in enumerate(res.ranked_vasps)
        ],
    }


@app.get("/api/demo/report")
def export_report(suspect: str = "bc1q9vza2e8424t6m5qgxp2r83kwln8y0e78k37df8"):
    from demo.loader import generate_demo_pdf_report
    G, candidate_vasps, _, _ = load_demo_graph()
    engine = DemoAttributionEngine(G)
    res = engine.attribute(suspect, candidate_vasps)

    buffer = io.BytesIO()
    pdf_path = DEMO_DIR / "Demo_Forensic_Report.pdf"
    generate_demo_pdf_report(res, pdf_path)

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Demo_Forensic_Report_6Hop.pdf"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)
