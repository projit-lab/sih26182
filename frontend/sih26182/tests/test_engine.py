"""Smoke test: does the engine correctly identify an obvious true source
on a trivial hand-built graph before we trust it on anything harder?"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import networkx as nx
from src.attribution.engine import AttributionEngine

def test_simple_direct_case():
    G = nx.Graph()
    G.add_edge("VASP_true", "hop1", weight=5.0)
    G.add_edge("hop1", "suspect", weight=5.0)
    G.add_edge("VASP_decoy", "far_hop", weight=0.1)
    G.add_edge("far_hop", "suspect", weight=0.1)

    engine = AttributionEngine(G)
    result = engine.attribute("suspect", ["VASP_true", "VASP_decoy"])
    assert result.ranked_candidates[0] == "VASP_true", \
        f"Expected VASP_true to rank first, got {result.ranked_candidates}"
    print("PASS: simple direct case correctly attributed")

if __name__ == "__main__":
    test_simple_direct_case()
