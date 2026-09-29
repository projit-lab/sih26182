"""
API for the demo: loads real cached case data and exposes /attribute.

Uses audited src/attribution/engine.py AttributionEngine.
"""
import math
from contextlib import asynccontextmanager

import networkx as nx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.attribution.engine import AttributionEngine
from src.attribution.weights import _log_scale_weights
import json
from pathlib import Path

_CASES: dict = {}


def load_case(case_id: str) -> dict:
    case_dir = Path(f"data/cases/{case_id}")
    edges_file = case_dir / "edges.json"
    meta_file = case_dir / "meta.json"

    with open(meta_file, "r", encoding="utf-8") as f:
        meta = json.load(f)

    with open(edges_file, "r", encoding="utf-8") as f:
        edges = json.load(f)

    G = nx.Graph()
    for e in edges:
        # weights are already log-scaled, so we just add them
        G.add_edge(e["source"], e["target"], **e)

    return {
        "graph": G,
        "candidate_vasps": meta["candidates"],
        "suspect": meta["suspect"],
        "truncated": meta.get("truncated", False),
        "degree_correction": meta.get("degree_correction", False),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    cases_dir = Path("data/cases")
    if cases_dir.exists():
        for case_dir in cases_dir.iterdir():
            if case_dir.is_dir() and (case_dir / "meta.json").exists():
                _CASES[case_dir.name] = load_case(case_dir.name)
    yield


app = FastAPI(title="SIH26182 Wallet Attribution Engine", lifespan=lifespan)


class AttributionRequest(BaseModel):
    case_id: str = "silkroad"
    suspect_wallet: str | None = None       # defaults to the case's known suspect if omitted
    candidate_vasps: list[str] | None = None  # defaults to all known exchange candidates in the case


@app.get("/cases")
def list_cases():
    return {
        case_id: {
            "nodes": data["graph"].number_of_nodes(),
            "edges": data["graph"].number_of_edges(),
            "suspect": data["suspect"],
            "candidate_count": len(data["candidate_vasps"]),
            "truncated": data["truncated"],
        }
        for case_id, data in _CASES.items()
    }


@app.get("/graph/health")
def graph_health(case_id: str = "silkroad"):
    if case_id not in _CASES:
        raise HTTPException(status_code=404, detail=f"Unknown case_id '{case_id}'")
    engine = AttributionEngine(_CASES[case_id]["graph"])
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

    engine = AttributionEngine(case["graph"], degree_correction=case.get("degree_correction", False))
    try:
        result = engine.attribute(suspect, candidates)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    payload = result.to_json_dict()
    payload["case_id"] = req.case_id
    payload["truncated"] = case["truncated"]
    payload["graph"] = engine.graph_health()
    # attach human-readable VASP names for whatever candidates were scored
    payload["candidate_labels"] = {
        addr: case["candidate_vasps"].get(addr, addr) for addr in candidates
    }
    return payload


@app.get("/health")
def health():
    return {"status": "ok"}
