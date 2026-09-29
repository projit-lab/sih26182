import json
import math
from pathlib import Path
from datetime import datetime

from silkroad.loader import build_silkroad_graph
from src.attribution.weights import _log_scale_weights
from src.attribution.engine import AttributionEngine

def main():
    # Build the graph
    G_raw, _ = build_silkroad_graph()
    
    # Scale weights
    G = _log_scale_weights(G_raw)
    
    # Load tags
    tags_file = Path("silkroad/entity_tags.json")
    with open(tags_file, "r", encoding="utf-8") as f:
        tags_data = json.load(f)
        
    suspect = None
    candidates = {}
    for t in tags_data:
        if t.get("category") == "illicit":
            suspect = t["address"]
        elif t.get("category") == "exchange":
            candidates[t["address"]] = t.get("entity_name", t["address"])
            
    # Write edges
    edges_list = []
    for u, v, data in G.edges(data=True):
        edges_list.append({
            "source": u,
            "target": v,
            "weight": data.get("weight"),
            "amount_satoshis": data.get("amount_satoshis"),
            "tx_hash": data.get("tx_hash")
        })
        
    out_dir = Path("data/cases/silkroad")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    with open(out_dir / "edges.json", "w", encoding="utf-8") as f:
        json.dump(edges_list, f, indent=2)
        
    # Run null tests
    engine = AttributionEngine(G, degree_correction=False)
    candidates_list = list(candidates.keys())
    exclude = {suspect, *candidates_list}
    
    runs = [
        {"n": 40, "seed": 0},
        {"n": 40, "seed": 1},
        {"n": 40, "seed": 2},
        {"n": 200, "seed": 0},
    ]
    
    null_test_results = []
    true_count = 0
    
    for r in runs:
        res = engine.null_test(candidates_list, exclude, n=r["n"], seed=r["seed"])
        res["n_requested"] = r["n"]
        res["seed"] = r["seed"]
        null_test_results.append(res)
        if res.get("likely_needs_degree_correction"):
            true_count += 1
            
    majority = true_count > (len(runs) / 2)
    
    # Meta dict
    meta = {
        "truncated": False,
        "source_file": "silkroad/subgraph_edges.json",
        "weighting": "log1p(amount_satoshis)",
        "suspect": suspect,
        "candidates": candidates,
        "degree_correction": majority,
        "null_test": null_test_results,
        "generated": datetime.utcnow().isoformat()
    }
    
    with open(out_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

if __name__ == "__main__":
    main()
