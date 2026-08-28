"""
Minimal API for the demo: load a graph, expose /attribute endpoint.
Swap `load_demo_graph()` for real ingestion once real data is available --
everything downstream (engine, API, UI) stays unchanged.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import networkx as nx

from src.attribution.engine import AttributionEngine

app = FastAPI(title="SIH26182 Wallet Attribution Engine")

_engine: AttributionEngine | None = None


def load_demo_graph() -> nx.Graph:
    """Placeholder graph loader -- replace with src/ingestion output."""
    G = nx.Graph()
    # TODO: replace with real/synthetic graph loader from src/ingestion
    return G


@app.on_event("startup")
def startup():
    global _engine
    graph = load_demo_graph()
    _engine = AttributionEngine(graph)


class AttributionRequest(BaseModel):
    suspect_wallet: str
    candidate_vasps: list[str]


@app.post("/attribute")
def attribute(req: AttributionRequest):
    if _engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    try:
        result = _engine.attribute(req.suspect_wallet, req.candidate_vasps)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "suspect": result.suspect,
        "ranked_candidates": result.ranked_candidates,
        "scores": result.scores,
        "method": result.method,
    }


@app.get("/health")
def health():
    return {"status": "ok"}
