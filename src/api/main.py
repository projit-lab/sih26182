"""
API for the demo: loads real cached case data and exposes /attribute.

Uses audited src/attribution/engine.py AttributionEngine.
"""
import math
import json
from pathlib import Path
from contextlib import asynccontextmanager

import networkx as nx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.attribution.engine import AttributionEngine, outward_reachable_subgraph
from src.attribution.weights import _log_scale_weights

_CASES: dict = {}
_TAGS: dict = {}

def load_case(case_id: str) -> dict:
    case_dir = Path(f"data/cases/{case_id}")
    edges_file = case_dir / "edges.json"
    meta_file = case_dir / "meta.json"

    with open(meta_file, "r", encoding="utf-8") as f:
        meta = json.load(f)

    with open(edges_file, "r", encoding="utf-8") as f:
        edges = json.load(f)

    G = nx.DiGraph()
    for e in edges:
        G.add_edge(e["source"], e["target"], **e)

    return {
        "graph": G,
        "candidate_vasps": meta["candidates"],
        "suspect": meta["suspect"],
        "truncated": meta.get("truncated", False),
        "degree_correction": meta.get("degree_correction", False),
        "null_test_runs": meta.get("null_test", []),
    }

@asynccontextmanager
async def lifespan(app: FastAPI):
    cases_dir = Path("data/cases")
    if cases_dir.exists():
        for case_dir in cases_dir.iterdir():
            if case_dir.is_dir() and (case_dir / "meta.json").exists():
                _CASES[case_dir.name] = load_case(case_dir.name)
                
    tags_file = Path("silkroad/entity_tags.json")
    if tags_file.exists():
        with open(tags_file, "r", encoding="utf-8") as f:
            for t in json.load(f):
                _TAGS[t["address"]] = t
    yield

app = FastAPI(title="SIH26182 Wallet Attribution Engine", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AttributionRequest(BaseModel):
    case_id: str = "silkroad"
    suspect_wallet: str | None = None
    candidate_vasps: list[str] | None = None
    direction: str = "undirected"

@app.get("/cases")
def list_cases():
    out = {}
    for case_id, data in _CASES.items():
        G = nx.Graph(data["graph"])
        n_components = nx.number_connected_components(G)
        try:
            suspect_component_size = len(nx.node_connected_component(G, data["suspect"]))
        except KeyError:
            suspect_component_size = 0
            
        out[case_id] = {
            "suspect": data["suspect"],
            "nodes": data["graph"].number_of_nodes(),
            "edges": data["graph"].number_of_edges(),
            "n_components": n_components,
            "suspect_component_size": suspect_component_size,
            "truncated": data["truncated"],
        }
    return out

@app.get("/graph/health")
def graph_health(case_id: str = "silkroad"):
    if case_id not in _CASES:
        raise HTTPException(status_code=404, detail=f"Unknown case_id '{case_id}'")
    engine = AttributionEngine(nx.Graph(_CASES[case_id]["graph"]))
    return engine.graph_health()

@app.post("/attribute")
def attribute(req: AttributionRequest):
    if req.case_id not in _CASES:
        raise HTTPException(status_code=404, detail=f"Unknown case_id '{req.case_id}'")
    case = _CASES[req.case_id]

    suspect = req.suspect_wallet or case["suspect"]
    if suspect is None:
        raise HTTPException(status_code=400, detail="No suspect_wallet given and case has no default")

    candidates = req.candidate_vasps or list(case["candidate_vasps"].keys())

    DG = case["graph"]
    try:
        if req.direction == "outward":
            G = outward_reachable_subgraph(DG, suspect)
        else:
            G = nx.Graph(DG)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    engine = AttributionEngine(G, degree_correction=case.get("degree_correction", False))
    try:
        result = engine.attribute(suspect, candidates)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    payload = result.to_json_dict()
    payload["case_id"] = req.case_id
    payload["truncated"] = case["truncated"]
    payload["direction"] = req.direction
    payload["graph"] = engine.graph_health()
    
    candidate_labels = {}
    for addr in candidates:
        candidate_labels[addr] = case["candidate_vasps"].get(addr, addr)
    payload["candidate_labels"] = candidate_labels

    try:
        comp_nodes = nx.node_connected_component(G, suspect)
    except KeyError:
        comp_nodes = set()
        
    g_nodes = []
    label_sources = {}
    for node in comp_nodes:
        tag = _TAGS.get(node, {})
        label = tag.get("entity_name", node[:8] + "...")
        if tag.get("source"):
            label_sources[node] = tag["source"]
            
        if node == suspect:
            role = "suspect"
        elif node in candidates:
            role = "candidate_vasp"
        else:
            role = "hop"
        g_nodes.append({
            "id": node,
            "label": label,
            "role": role
        })
        
    g_edges = []
    for u, v, d in DG.edges(data=True):
        if u in comp_nodes and v in comp_nodes:
            amt = d.get("amount_satoshis", 0)
            g_edges.append({
                "id": f"{u}-{v}-{d.get('tx_hash', '')}",
                "source": u,
                "target": v,
                "amountSatoshis": amt,
                "amountBtc": amt / 1e8,
                "txHash": d.get("tx_hash", "")
            })
            
    payload["graph_elements"] = {"nodes": g_nodes, "edges": g_edges}
    payload["label_sources"] = label_sources
    
    try:
        paths = nx.single_source_shortest_path_length(G, suspect)
    except Exception:
        paths = {}
    payload["hop_depths"] = {c: paths.get(c) for c in candidates}
    
    def weight_func(u, v, d):
        return 1.0 / max(1e-9, d.get("weight", 1.0))
        
    d_paths = {}
    for c in candidates:
        try:
            d_paths[c] = nx.dijkstra_path_length(G, suspect, c, weight=weight_func)
        except nx.NetworkXNoPath:
            pass
            
    if d_paths:
        winner = min(d_paths, key=d_paths.get)
        winner_name = candidate_labels.get(winner, winner)
        hop_count = paths.get(winner, 0)
    else:
        winner = None
        winner_name = "None"
        hop_count = 0
        
    if winner and result.ranked_candidates and winner != result.ranked_candidates[0]:
        eff_winner = result.ranked_candidates[0]
        flaw = f"Shortest path picks {winner_name}; effective resistance picks {candidate_labels.get(eff_winner, eff_winner)}"
    else:
        flaw = "Shortest path agrees with effective resistance on this case"
        
    payload["dijkstra_comparison"] = {
        "winner": winner,
        "winner_name": winner_name,
        "hop_count": hop_count,
        "flaw": flaw
    }

    return payload

@app.get("/health")
def health():
    return {"status": "ok"}
