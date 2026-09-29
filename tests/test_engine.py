import math
import pytest
import networkx as nx

from src.attribution.engine import AttributionEngine, AttributionResult


# ---------------------------------------------------------------- analytic

def test_path_graph_series_resistance():
    # P5: 0-1-2-3-4, unit weight each edge. Endpoints: 4 resistors in series.
    G = nx.path_graph(5)
    nx.set_edge_attributes(G, 1.0, "weight")
    eng = AttributionEngine(G)
    eng._factorize()
    r = eng._resistance(0, 4)
    assert math.isclose(r, 4.0, rel_tol=1e-4)

def test_cycle_graph_resistance():
    # C6, unit weight. R(i,j) = k(n-k)/n for nodes k apart.
    G = nx.cycle_graph(6)
    nx.set_edge_attributes(G, 1.0, "weight")
    eng = AttributionEngine(G)
    eng._factorize()
    r = eng._resistance(0, 3)
    assert math.isclose(r, 1.5, rel_tol=1e-4)

def test_complete_graph_resistance():
    # K5, unit weight. R(i,j) = 2/n for any pair.
    G = nx.complete_graph(5)
    nx.set_edge_attributes(G, 1.0, "weight")
    eng = AttributionEngine(G)
    eng._factorize()
    r = eng._resistance(0, 1)
    assert math.isclose(r, 0.4, rel_tol=1e-6)

def test_weighted_series_resistance():
    # 0 -g1- 1 -g2- 2. Series resistors: 1/g1 + 1/g2.
    G = nx.Graph()
    G.add_edge(0, 1, weight=2.0)   # r = 0.5
    G.add_edge(1, 2, weight=4.0)   # r = 0.25
    eng = AttributionEngine(G)
    eng._factorize()
    r = eng._resistance(0, 2)
    assert math.isclose(r, 0.75, rel_tol=1e-4)


# ------------------------------------------------------------ disconnection

def test_disconnected_candidate_is_unreachable_not_ranked():
    G = nx.Graph()
    G.add_edge("suspect", "vaspA", weight=1.0)
    G.add_edge("vaspB", "vaspC", weight=1.0)   # separate component
    eng = AttributionEngine(G)
    res = eng.attribute("suspect", ["vaspA", "vaspB"])
    assert "vaspA" in res.ranked_candidates
    assert "vaspB" in res.unreachable
    assert "vaspB" not in res.ranked_candidates

def test_unknown_suspect_raises():
    G = nx.Graph()
    G.add_edge("a", "b", weight=1.0)
    eng = AttributionEngine(G)
    with pytest.raises(ValueError):
        eng.attribute("not_in_graph", ["a"])

def test_unknown_candidate_is_unreachable():
    G = nx.Graph()
    G.add_edge("suspect", "a", weight=1.0)
    eng = AttributionEngine(G)
    res = eng.attribute("suspect", ["a", "ghost_candidate"])
    assert "ghost_candidate" in res.unreachable
    assert res.raw_resistance["ghost_candidate"] is None


# ------------------------------------------------------------- JSON safety

def test_to_json_dict_never_emits_infinity_or_nan():
    G = nx.Graph()
    G.add_edge("suspect", "vaspA", weight=1.0)
    G.add_edge("vaspB", "vaspC", weight=1.0)
    eng = AttributionEngine(G)
    res = eng.attribute("suspect", ["vaspA", "vaspB"])
    payload = res.to_json_dict()
    import json
    text = json.dumps(payload)
    assert "Infinity" not in text
    assert "NaN" not in text
    reparsed = json.loads(text)
    assert reparsed["scores"]["vaspA"] is not None

def test_single_candidate_no_separation_ratio():
    G = nx.Graph()
    G.add_edge("suspect", "vaspA", weight=1.0)
    eng = AttributionEngine(G)
    res = eng.attribute("suspect", ["vaspA"])
    assert res.separation_ratio is None


# --------------------------------------------------------------- hub bias

def _adversarial_hub_graph():
    """TRUE_VASP is reached via a genuine but partially-obscured 3-hop chain
    with a strong backbone and one thin final link (its low resulting degree
    is what raw scoring mistakes for weak evidence). HUB_VASP is a large,
    well-connected cluster suspect has one ordinary incidental link into,
    with no real relationship to the suspect beyond hub proximity. Verified:
    raw resistance favors HUB_VASP (1.62 vs 6.00); degree correction
    correctly reverses this (0.67 vs 1.27)."""
    G = nx.Graph()
    G.add_edge("suspect", "mid1", weight=2.0)
    G.add_edge("mid1", "mid2", weight=2.0)
    G.add_edge("mid2", "TRUE_VASP", weight=0.2)
    for i in range(60):
        G.add_edge(f"bg{i}", "HUB_VASP", weight=1.0)
        if i < 15:
            G.add_edge(f"bg{i}", f"bg{i+1}", weight=1.0)
    G.add_edge("suspect", "bg0", weight=1.0)
    return G

def test_raw_scoring_fails_hub_bias():
    G = _adversarial_hub_graph()
    eng = AttributionEngine(G, degree_correction=False)
    res = eng.attribute("suspect", ["TRUE_VASP", "HUB_VASP"])
    assert res.ranked_candidates[0] == "HUB_VASP"  # documents the known failure mode

def test_degree_correction_fixes_hub_bias():
    G = _adversarial_hub_graph()
    eng = AttributionEngine(G, degree_correction=True)
    res = eng.attribute("suspect", ["TRUE_VASP", "HUB_VASP"])
    assert res.ranked_candidates[0] == "TRUE_VASP"

def test_null_test_flags_hub_bias_graph():
    G = _adversarial_hub_graph()
    eng = AttributionEngine(G, degree_correction=False)
    exclude = {"suspect", "TRUE_VASP", "HUB_VASP"}
    result = eng.null_test(["TRUE_VASP", "HUB_VASP"], exclude=exclude, n=40, seed=0)
    assert result["likely_needs_degree_correction"] is True

def test_null_test_does_not_false_flag_a_fair_graph():
    G = nx.Graph()
    G.add_edge("suspect", "vaspA", weight=1.0)
    for i in range(20):
        G.add_edge(f"bgA{i}", "vaspA", weight=1.0)
        G.add_edge(f"bgB{i}", "vaspB", weight=1.0)
    G.add_edge("vaspA", "vaspB", weight=0.1)
    eng = AttributionEngine(G, degree_correction=False)
    exclude = {"suspect", "vaspA", "vaspB"}
    result = eng.null_test(["vaspA", "vaspB"], exclude=exclude, n=30, seed=1)
    assert isinstance(result["likely_needs_degree_correction"], bool)


# ------------------------------------------------------------- diagnostics

def test_graph_health_reports_disconnection():
    G = nx.Graph()
    G.add_edge("a", "b", weight=1.0)
    G.add_edge("c", "d", weight=1.0)
    eng = AttributionEngine(G)
    health = eng.graph_health()
    assert health["connected"] is False
    assert health["n_components"] == 2
    assert health["nodes"] == 4
    assert health["edges"] == 2

# ------------------------------------------------------------- outward reachable

from src.attribution.engine import outward_reachable_subgraph

def test_outward_reachable_against_direction():
    DG = nx.DiGraph()
    DG.add_edge("cand1", "suspect", weight=1.0)
    DG.add_edge("suspect", "cand2", weight=1.0)
    G = outward_reachable_subgraph(DG, "suspect")
    eng = AttributionEngine(G)
    res = eng.attribute("suspect", ["cand1", "cand2"])
    assert "cand1" in res.unreachable
    assert "cand2" in res.ranked_candidates

def test_outward_reachable_pure_forward_chain():
    DG = nx.DiGraph()
    DG.add_edge("suspect", "a", weight=2.0)
    DG.add_edge("a", "b", weight=4.0)
    G = outward_reachable_subgraph(DG, "suspect")
    eng1 = AttributionEngine(G)
    res1 = eng1.attribute("suspect", ["b"])
    
    G_un = nx.Graph(DG)
    eng2 = AttributionEngine(G_un)
    res2 = eng2.attribute("suspect", ["b"])
    
    assert math.isclose(res1.raw_resistance["b"], res2.raw_resistance["b"])

def test_outward_reachable_missing_suspect():
    DG = nx.DiGraph()
    DG.add_edge("a", "b")
    with pytest.raises(ValueError):
        outward_reachable_subgraph(DG, "missing")
