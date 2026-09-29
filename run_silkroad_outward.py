import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

import networkx as nx
from src.api.main import load_case
from src.attribution.engine import AttributionEngine, outward_reachable_subgraph

def main():
    case = load_case("silkroad")
    suspect = case["suspect"]
    candidates = list(case["candidate_vasps"].keys())
    deg_corr = case.get("degree_correction", False)

    DG = case["graph"] # Now DiGraph

    # Undirected
    G_un = nx.Graph(DG)
    eng_un = AttributionEngine(G_un, degree_correction=deg_corr)
    res_un = eng_un.attribute(suspect, candidates)

    # Outward
    G_out = outward_reachable_subgraph(DG, suspect)
    eng_out = AttributionEngine(G_out, degree_correction=deg_corr)
    res_out = eng_out.attribute(suspect, candidates)

    out = "\n--- Undirected ---\n"
    for idx, c in enumerate(res_un.ranked_candidates, 1):
        name = case["candidate_vasps"].get(c, c)
        out += f"#{idx} {name}: {res_un.scores[c]:.4f}\n"

    out += "\n--- Outward ---\n"
    for idx, c in enumerate(res_out.ranked_candidates, 1):
        name = case["candidate_vasps"].get(c, c)
        out += f"#{idx} {name}: {res_out.scores[c]:.4f}\n"
    
    out += f"\nUnreachable in outward: {[case['candidate_vasps'].get(c, c) for c in res_out.unreachable]}\n"

    print(out)
    
    with open("docs/results/silkroad_numbers.txt", "a") as f:
        f.write("\n\n=== Silk Road: Undirected vs Outward ===\n")
        f.write(out)

if __name__ == "__main__":
    main()
