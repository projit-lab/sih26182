"""
API for the demo: loads real cached case data and exposes /attribute.

Uses silkroad/loader.py's build_silkroad_graph() for the raw edge data, but
does NOT use silkroad/engine.py's SilkRoadAttributionEngine -- that solver
is unaudited (separate implementation, raw BTC weighting, not covered by
the adversarial review in docs/ENGINE_CODE_REVIEW.md). This uses the
audited src/attribution/engine.py AttributionEngine instead, with weights
converted to log-scaled conductance here rather than mutating loader.py
(which other scripts may depend on in its current raw-BTC form).
"""
import math
from contextlib import asynccontextmanager

import networkx as nx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.attribution.engine import AttributionEngine
from silkroad.loader import build_silkroad_graph
import json
from pathlib import Path

_CASES: dict = {}


def _log_scale_weights(G: nx.Graph) -> nx.Graph:
    """Replace raw-BTC edge weights with log1p(amount_satoshis) conductance.
    See docs/ENGINE_CODE_REVIEW.md Improvement A: raw amounts gave ~208x
    worse Laplacian conditioning on heavy-tailed real transaction data."""
    for u, v, data in G.edges(data=True):
        sats = data.get("amount_satoshis")
        if sats is not None:
            data["weight"] = math.log1p(float(sats))
    return G


def _load_silkroad_case() -> dict:
    G, candidate_vasps = build_silkroad_graph()
    G = _log_scale_weights(G)

    # Determine the suspect address from entity_tags.json (category == "illicit")
    # rather than hardcoding it, so this generalizes to future cases.
    tags_file = Path("silkroad/entity_tags.json")
    suspect = None
    with open(tags_file, "r", encoding="utf-8") as f:
        tags_data = json.load(f)
    for t in tags_data:
        if t.get("category") == "illicit":
            suspect = t["address"]
            break

    return {
        "graph": G,
        "candidate_vasps": candidate_vasps,   # address -> entity_name
        "suspect": suspect,
        "truncated": False,   # this case is the fully-verified 199/235 extraction
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    _CASES["silkroad"] = _load_silkroad_case()
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

    engine = AttributionEngine(case["graph"])
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
