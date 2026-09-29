import sqlite3
import json
import glob
import networkx as nx
from collections import defaultdict, Counter
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.attribution.weights import _log_scale_weights
from validation.attribution_methods_baselines import build_laplacian, factorize_laplacian, effective_resistance_rank, prepare_shortest_path_graph, shortest_path_rank

def top_k(ranked, gt, k):
    return 1.0 if gt in ranked[:k] else 0.0

def main():
    db = sqlite3.connect('backend/data/attribution.duckdb')
    c = db.cursor()
    
    rows = c.execute('SELECT address, entity_name, source FROM entity_tags WHERE category="exchange"').fetchall()
    
    print("=== Tag Sources (Exchange category) BEFORE filtering ===")
    source_counts = Counter([r[2] for r in rows])
    for k, v in source_counts.items():
        print(f"{k}: {v}")
    
    valid_tags = []
    for address, name, source in rows:
        if source in ('DemoSeed', 'Synthetic-Elliptic-style') or str(source).startswith('Team label'):
            continue
        valid_tags.append((address, name, source))
    
    G = nx.Graph()
    try:
        edges_db = c.execute('SELECT source_address, target_address, amount_satoshis FROM transaction_edges').fetchall()
        for src, dst, sats in edges_db:
            if not G.has_edge(src, dst):
                G.add_edge(src, dst, amount_satoshis=0.0)
            G[src][dst]['amount_satoshis'] += float(sats)
    except sqlite3.OperationalError:
        pass
        
    for f in glob.glob('data/cases/*/edges.json'):
        with open(f, 'r') as fh:
            data = json.load(fh)
            for e in data:
                src, dst = e['source'], e['target']
                sats = float(e['amount_satoshis'])
                if not G.has_edge(src, dst):
                    G.add_edge(src, dst, amount_satoshis=0.0)
                G[src][dst]['amount_satoshis'] += sats
                
    G = _log_scale_weights(G)
        
    entity_to_addrs = defaultdict(list)
    for addr, name, src in valid_tags:
        if addr in G:
            entity_to_addrs[name].append(addr)
            
    eligible_entities = {k: v for k, v in entity_to_addrs.items() if len(v) >= 2}
    print(f"\nEligible entities (>= 2 addresses in graph): {len(eligible_entities)}")
    for k, v in eligible_entities.items():
        print(f"  {k}: {len(v)} addresses")
        
    if len(eligible_entities) < 2:
        out = "Not measurable with current cached data\n\n"
        out += "=== Tag Sources (Exchange category) BEFORE filtering ===\n"
        for k, v in source_counts.items():
            out += f"{k}: {v}\n"
        out += f"\nEligible entities: {len(eligible_entities)}\n"
        with open('docs/results/real_world_precision.md', 'w') as f:
            f.write(out)
        print("Stopping.")
        sys.exit(0)

    # Leave-one-out
    print("\nRunning leave-one-out evaluation...")
    H = prepare_shortest_path_graph(G)
    L, idx, nodelist = build_laplacian(G)
    n = L.shape[0]
    lu = factorize_laplacian(L)

    sp_top1 = []
    sp_top3 = []
    er_top1 = []
    er_top3 = []

    for gt_entity, addrs in eligible_entities.items():
        for suspect_addr in addrs:
            # Candidates: all other eligible addresses
            candidate_addrs = []
            candidate_map = {}
            for e_name, e_addrs in eligible_entities.items():
                for a in e_addrs:
                    if a != suspect_addr:
                        candidate_addrs.append(a)
                        candidate_map[a] = e_name
            
            # SP
            ranked_sp, _ = shortest_path_rank(H, suspect_addr, candidate_addrs)
            # entity score = min over addresses = first address encountered for that entity
            ranked_entities_sp = []
            for a in ranked_sp:
                en = candidate_map[a]
                if en not in ranked_entities_sp:
                    ranked_entities_sp.append(en)
            sp_top1.append(top_k(ranked_entities_sp, gt_entity, 1))
            sp_top3.append(top_k(ranked_entities_sp, gt_entity, 3))

            # ER
            ranked_er, _ = effective_resistance_rank(suspect_addr, candidate_addrs, lu, idx, n)
            ranked_entities_er = []
            for a in ranked_er:
                en = candidate_map[a]
                if en not in ranked_entities_er:
                    ranked_entities_er.append(en)
            er_top1.append(top_k(ranked_entities_er, gt_entity, 1))
            er_top3.append(top_k(ranked_entities_er, gt_entity, 3))
            
    print("\n=== Results (Leave-One-Out) ===")
    print(f"Total queries: {len(sp_top1)}")
    print(f"Shortest Path Top-1: {sum(sp_top1)/len(sp_top1):.3f}")
    print(f"Shortest Path Top-3: {sum(sp_top3)/len(sp_top3):.3f}")
    print(f"Effective Resistance Top-1: {sum(er_top1)/len(er_top1):.3f}")
    print(f"Effective Resistance Top-3: {sum(er_top3)/len(er_top3):.3f}")
    print(f"Chance Top-1: {1.0 / len(eligible_entities):.3f}")

if __name__ == "__main__":
    main()
