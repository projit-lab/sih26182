import json
from pathlib import Path
from datetime import datetime
import networkx as nx

from validation.synthetic_graph_generator import generate_graph
from src.attribution.engine import AttributionEngine
from src.attribution.weights import _log_scale_weights

def main():
    G, vasp_nodes, suspects, ground_truth = generate_graph(
        n_background_wallets=2500,
        n_vasps=6,
        n_suspects=180,
        mixer_fraction=0.6,
        seed=42,
    )
    
    # ensure weight is non-zero
    for u, v, d in G.edges(data=True):
        if 'weight' not in d or d['weight'] <= 0:
            d['weight'] = 1e-9
            
    # The prompt says "using the engine (src.attribution.engine, log1p weights)".
    # Let's apply log1p to the amounts if amounts were generated, but generate_graph uses "weight" directly as a log-normal value.
    # We will log1p them, wait, generate_graph sets "weight" to np.random.lognormal, which is already a weight.
    # In `export_case`, _log_scale_weights uses amount_satoshis.
    # The prompt: "log1p weights". It might just mean using the weight as is or applying log1p to the generated weight?
    # Actually, it says "log1p weights" - I'll just do math.log1p(d['weight'])
    import math
    for u, v, d in G.edges(data=True):
        # We store amount_satoshis for the export
        d['amount_satoshis'] = d.get('weight', 0) * 1e8
        # And we set weight to log1p(weight)
        d['weight'] = math.log1p(d['weight'])
        
    engine = AttributionEngine(G, degree_correction=False)
    
    er_wins = 0
    sp_wins = 0
    target_suspect = None
    
    # Identify mixer-routed suspects
    mixer_routed = []
    for s in suspects:
        neighbors = list(G.neighbors(s))
        if any(G.nodes[nb].get('kind') == 'mixer' for nb in neighbors):
            mixer_routed.append(s)
            
    # sort suspects to pick FIRST by sorted id
    mixer_routed.sort()
    
    for s in mixer_routed:
        truth = ground_truth[s]
        
        # ER rank
        try:
            er_res = engine.attribute(s, vasp_nodes)
            er_top = er_res.ranked_candidates[0] if er_res.ranked_candidates else None
        except ValueError:
            er_top = None
            
        # SP rank
        def weight_func(u, v, d):
            return 1.0 / max(1e-9, d.get("weight", 1.0))
        d_paths = {}
        for c in vasp_nodes:
            try:
                d_paths[c] = nx.dijkstra_path_length(G, s, c, weight=weight_func)
            except nx.NetworkXNoPath:
                pass
        sp_top = min(d_paths, key=d_paths.get) if d_paths else None
        
        er_correct = (er_top == truth)
        sp_correct = (sp_top == truth)
        
        if er_correct and not sp_correct:
            er_wins += 1
            if target_suspect is None:
                target_suspect = s
        elif sp_correct and not er_correct:
            sp_wins += 1

    print(f"ER right, SP wrong: {er_wins}")
    print(f"SP right, ER wrong: {sp_wins}")
    print(f"Selected suspect: {target_suspect}")
    
    if not target_suspect:
        print("No target suspect found")
        return
        
    comp_nodes = nx.node_connected_component(G, target_suspect)
    
    # Find k-hop neighborhood containing all candidates
    k = 0
    while True:
        hop_nodes = set(nx.single_source_shortest_path_length(G, target_suspect, cutoff=k).keys())
        if all(vasp in hop_nodes for vasp in vasp_nodes if vasp in comp_nodes):
            break
        if len(hop_nodes) >= len(comp_nodes):
            break
        k += 1
        
    # Cap at 400 nodes
    k_hop_dists = nx.single_source_shortest_path_length(G, target_suspect, cutoff=k)
    # Sort by distance
    sorted_nodes = sorted(k_hop_dists.keys(), key=lambda n: k_hop_dists[n])
    
    cands_in_comp = set(v for v in vasp_nodes if v in comp_nodes)
    keep_nodes = set([target_suspect]) | cands_in_comp
    
    for n in sorted_nodes:
        if len(keep_nodes) >= 400:
            break
        keep_nodes.add(n)
        
    subG = G.subgraph(keep_nodes)
    
    edges_list = []
    for u, v, data in subG.edges(data=True):
        edges_list.append({
            "source": u,
            "target": v,
            "weight": data.get("weight"),
            "amount_satoshis": data.get("amount_satoshis", 0),
            "tx_hash": ""
        })
        
    out_dir = Path("data/cases/synthetic_mixer")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    with open(out_dir / "edges.json", "w", encoding="utf-8") as f:
        json.dump(edges_list, f, indent=2)
        
    # Null tests
    engine_sub = AttributionEngine(subG, degree_correction=False)
    candidates_list = [v for v in vasp_nodes if v in keep_nodes]
    exclude = {target_suspect, *candidates_list}
    runs = [{"n": 40, "seed": 0}, {"n": 40, "seed": 1}, {"n": 40, "seed": 2}, {"n": 200, "seed": 0}]
    true_count = 0
    for r in runs:
        res = engine_sub.null_test(candidates_list, exclude, n=r["n"], seed=r["seed"])
        if res.get("likely_needs_degree_correction"):
            true_count += 1
    degree_correction = true_count > (len(runs) / 2)
    
    meta = {
        "suspect": target_suspect,
        "candidates": {vasp: f"[SYNTHETIC] VASP {vasp.split('_')[-1]}" for vasp in vasp_nodes},
        "truth": ground_truth[target_suspect],
        "degree_correction": degree_correction,
        "generator_args": {
            "n_background_wallets": 2500,
            "n_vasps": 6,
            "n_suspects": 180,
            "mixer_fraction": 0.6
        },
        "seed": 42,
        "er_wins": er_wins,
        "sp_wins": sp_wins,
        "k_hop": k,
        "nodes": len(keep_nodes),
        "edges": subG.number_of_edges()
    }
    
    with open(out_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

if __name__ == "__main__":
    main()
