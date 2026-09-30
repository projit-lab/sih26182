import numpy as np
import networkx as nx
from collections import defaultdict
import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from validation.synthetic_graph_generator import generate_graph
from validation.attribution_methods_baselines import (
    build_laplacian, factorize_laplacian, effective_resistance_rank
)
from src.attribution.engine import AttributionEngine

def run_seed(seed):
    G, vasp_nodes, suspects, ground_truth = generate_graph(
        n_background_wallets=2500, n_vasps=6, n_suspects=180,
        mixer_fraction=0.5, seed=seed
    )
    
    comps = list(nx.connected_components(G))
    n_comps = len(comps)
    
    # Identify component index for each node
    comp_of = {}
    for i, c in enumerate(comps):
        for n in c:
            comp_of[n] = i
            
    vasp_comps = {comp_of[v] for v in vasp_nodes}
    
    # Background nodes: non-suspect, non-VASP
    bg_pool = [n for n in G.nodes() if n not in suspects and n not in vasp_nodes]
    rng = np.random.default_rng(seed)
    bg_sample = rng.choice(bg_pool, min(200, len(bg_pool)), replace=False)
    
    # Setup Method (a)
    L, idx, nodelist = build_laplacian(G)
    lu = factorize_laplacian(L)
    n_nodes = L.shape[0]
    
    # Setup Method (b)
    engine = AttributionEngine(G)
    engine._factorize()
    
    # Metrics
    same_comp_top1 = []
    diff_comp_top1 = []
    
    a_finite_diff = 0
    b_unreachable_diff = 0
    total_diff_queries = 0
    
    for s in bg_sample:
        s_comp = comp_of[s]
        is_same = s_comp in vasp_comps
        
        # Method (a)
        ranked_a, res_a = effective_resistance_rank(s, vasp_nodes, lu, idx, n_nodes)
        top1_a = ranked_a[0]
        
        if is_same:
            same_comp_top1.append(top1_a)
        else:
            diff_comp_top1.append(top1_a)
            
        # Check bug occurrences
        for v in vasp_nodes:
            if comp_of[v] != s_comp:
                total_diff_queries += 1
                if np.isfinite(res_a[v]):
                    a_finite_diff += 1
                    
        # Method (b)
        res_b = engine.attribute(s, vasp_nodes)
        for v in vasp_nodes:
            if comp_of[v] != s_comp:
                if v in res_b.unreachable:
                    b_unreachable_diff += 1
                    
    return {
        "seed": seed,
        "n_comps": n_comps,
        "same_comp_top1": same_comp_top1,
        "diff_comp_top1": diff_comp_top1,
        "a_finite_diff": a_finite_diff,
        "b_unreachable_diff": b_unreachable_diff,
        "total_diff_queries": total_diff_queries,
        "n_vasps": len(vasp_nodes)
    }

def analyze_group(group_name, top1_list, n_vasps):
    if not top1_list:
        return f"{group_name}: 0 queries"
    counts = defaultdict(int)
    for v in top1_list:
        counts[v] += 1
    total = len(top1_list)
    max_share = max(counts.values()) / total
    chance = 1.0 / n_vasps
    
    lines = [f"{group_name} (n={total}):"]
    for v, c in sorted(counts.items(), key=lambda x: -x[1]):
        lines.append(f"  {v}: {c/total:.1%} ({c})")
    lines.append(f"  Max share: {max_share:.1%} vs chance {chance:.1%}")
    return "\n".join(lines)

def main():
    seeds = [1, 2, 3, 4, 5]
    results = [run_seed(s) for s in seeds]
    
    same_all = []
    diff_all = []
    a_fin = 0
    b_unr = 0
    tot_diff = 0
    
    print("--- Graph Stats per Seed ---")
    for r in results:
        print(f"Seed {r['seed']}: {r['n_comps']} components")
        same_all.extend(r["same_comp_top1"])
        diff_all.extend(r["diff_comp_top1"])
        a_fin += r["a_finite_diff"]
        b_unr += r["b_unreachable_diff"]
        tot_diff += r["total_diff_queries"]
        n_vasps = r["n_vasps"]
        
    print("\n" + analyze_group("Same-Component Queries", same_all, n_vasps))
    print("\n" + analyze_group("Different-Component Queries", diff_all, n_vasps))
    
    print(f"\nBug isolation check on different-component candidate evaluations (total={tot_diff}):")
    print(f"  Method (a) gave finite score: {a_fin}/{tot_diff} ({a_fin/tot_diff if tot_diff else 0:.1%})")
    print(f"  Method (b) marked unreachable: {b_unr}/{tot_diff} ({b_unr/tot_diff if tot_diff else 0:.1%})")

if __name__ == "__main__":
    main()
