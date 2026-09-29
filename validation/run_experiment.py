import time
import numpy as np
from validation.synthetic_graph_generator import generate_graph
from validation.attribution_methods_baselines import (
    prepare_shortest_path_graph, shortest_path_rank,
    build_laplacian, factorize_laplacian, effective_resistance_rank,
    graphsage_rank_all,
)

def mrr(ranked_list, true_item):
    for i, item in enumerate(ranked_list):
        if item == true_item:
            return 1.0 / (i + 1)
    return 0.0

def top1(ranked_list, true_item):
    return 1.0 if ranked_list[0] == true_item else 0.0

def evaluate(method_name, per_suspect_ranks, ground_truth, suspects, obfuscated_flags):
    rows = []
    for s in suspects:
        ranked = per_suspect_ranks[s]
        gt = ground_truth[s]
        rows.append({
            "suspect": s,
            "top1": top1(ranked, gt),
            "mrr": mrr(ranked, gt),
            "obfuscated": obfuscated_flags[s],
        })
    all_top1 = np.mean([r["top1"] for r in rows])
    all_mrr = np.mean([r["mrr"] for r in rows])

    obf_rows = [r for r in rows if r["obfuscated"]]
    direct_rows = [r for r in rows if not r["obfuscated"]]

    obf_top1 = np.mean([r["top1"] for r in obf_rows]) if obf_rows else float('nan')
    obf_mrr = np.mean([r["mrr"] for r in obf_rows]) if obf_rows else float('nan')
    dir_top1 = np.mean([r["top1"] for r in direct_rows]) if direct_rows else float('nan')
    dir_mrr = np.mean([r["mrr"] for r in direct_rows]) if direct_rows else float('nan')

    print(f"\n=== {method_name} ===")
    print(f"  Overall      : Top-1 = {all_top1:.3f}   MRR = {all_mrr:.3f}   (n={len(rows)})")
    print(f"  MIXER-routed : Top-1 = {obf_top1:.3f}   MRR = {obf_mrr:.3f}   (n={len(obf_rows)})  <-- the hard/realistic cases")
    print(f"  Direct-path  : Top-1 = {dir_top1:.3f}   MRR = {dir_mrr:.3f}   (n={len(direct_rows)})  <-- the easy cases")
    return {
        "method": method_name, "all_top1": all_top1, "all_mrr": all_mrr,
        "obf_top1": obf_top1, "obf_mrr": obf_mrr, "dir_top1": dir_top1, "dir_mrr": dir_mrr,
    }


def main():
    print("Generating synthetic obfuscated wallet-transaction graph...")
    G, vasp_nodes, suspects, ground_truth = generate_graph(
        n_background_wallets=2500,
        n_vasps=6,
        n_suspects=180,
        mixer_fraction=0.6,
        seed=42,
    )
    print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # figure out which suspects were mixer-routed (ground truth bookkeeping for analysis)
    # we infer this by checking whether the suspect has any 'mixer' neighbor
    obfuscated_flags = {}
    for s in suspects:
        neighbors = list(G.neighbors(s))
        is_mixer_routed = any(G.nodes[nb].get('kind') == 'mixer' for nb in neighbors)
        obfuscated_flags[s] = is_mixer_routed
    n_obf = sum(obfuscated_flags.values())
    print(f"Mixer-routed suspects: {n_obf} / {len(suspects)}  (direct-path suspects: {len(suspects)-n_obf})")

    results_summary = []

    # ---------------- Method 1: Shortest Path ----------------
    t0 = time.time()
    H = prepare_shortest_path_graph(G)
    sp_ranks = {}
    for s in suspects:
        ranked, _ = shortest_path_rank(H, s, vasp_nodes)
        sp_ranks[s] = ranked
    t_sp = time.time() - t0
    print(f"\n[Shortest Path] computed in {t_sp:.2f}s")
    results_summary.append(evaluate("Shortest Path (obvious baseline)", sp_ranks, ground_truth, suspects, obfuscated_flags))

    # ---------------- Method 2: Effective Resistance ----------------
    t0 = time.time()
    L, idx, nodelist = build_laplacian(G)
    n = L.shape[0]
    lu = factorize_laplacian(L)
    print(f"[Effective Resistance] Laplacian factorized in {time.time()-t0:.2f}s")
    t1 = time.time()
    er_ranks = {}
    for s in suspects:
        ranked, _ = effective_resistance_rank(s, vasp_nodes, lu, idx, n)
        er_ranks[s] = ranked
    t_er = time.time() - t0
    print(f"[Effective Resistance] total (factorize + {len(suspects)} queries) in {t_er:.2f}s")
    results_summary.append(evaluate("Effective Resistance (our hypothesis)", er_ranks, ground_truth, suspects, obfuscated_flags))

    # ---------------- Method 3: GraphSAGE ----------------
    try:
        t0 = time.time()
        gs_results, final_loss = graphsage_rank_all(G, suspects, vasp_nodes, embedding_dim=32, epochs=80)
        gs_ranks = {s: gs_results[s][0] for s in suspects}
        t_gs = time.time() - t0
        print(f"\n[GraphSAGE] trained + inferred in {t_gs:.2f}s (final training loss: {final_loss:.4f})")
        results_summary.append(evaluate("GraphSAGE (learned embeddings, obvious ML baseline)", gs_ranks, ground_truth, suspects, obfuscated_flags))
    except ModuleNotFoundError:
        print("\n[GraphSAGE] Skipping GraphSAGE because 'torch' is not installed.")

    # ---------------- Summary table ----------------
    print("\n" + "=" * 100)
    print("SUMMARY -- the number that matters most is 'MIXER-routed' (realistic obfuscated case)")
    print("=" * 100)
    header = f"{'Method':45s} {'Overall Top1':>13s} {'Overall MRR':>12s} {'Mixer Top1':>11s} {'Mixer MRR':>10s} {'Direct Top1':>12s} {'Direct MRR':>11s}"
    print(header)
    print("-" * len(header))
    for r in results_summary:
        print(f"{r['method']:45s} {r['all_top1']:>13.3f} {r['all_mrr']:>12.3f} {r['obf_top1']:>11.3f} {r['obf_mrr']:>10.3f} {r['dir_top1']:>12.3f} {r['dir_mrr']:>11.3f}")

    return results_summary


if __name__ == "__main__":
    main()
