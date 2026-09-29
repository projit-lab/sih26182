import numpy as np
from validation.synthetic_graph_generator import generate_graph
from validation.attribution_methods_baselines import (
    prepare_shortest_path_graph, shortest_path_rank,
    build_laplacian, factorize_laplacian, effective_resistance_rank,
)

def top1(ranked, gt):
    return 1.0 if ranked[0] == gt else 0.0

def top3(ranked, gt):
    return 1.0 if gt in ranked[:3] else 0.0

def mrr(ranked, gt):
    for i, item in enumerate(ranked):
        if item == gt:
            return 1.0 / (i + 1)
    return 0.0

def run_seed(seed):
    G, vasp_nodes, suspects, ground_truth = generate_graph(
        n_background_wallets=2500, n_vasps=6, n_suspects=180,
        mixer_fraction=0.6, seed=seed,
    )
    obfuscated_flags = {}
    for s in suspects:
        neighbors = list(G.neighbors(s))
        obfuscated_flags[s] = any(G.nodes[nb].get('kind') == 'mixer' for nb in neighbors)

    H = prepare_shortest_path_graph(G)
    sp_top1_mixer, sp_top1_direct = [], []
    sp_top3_mixer, sp_top3_direct = [], []
    sp_mrr_mixer, sp_mrr_direct = [], []
    for s in suspects:
        ranked, _ = shortest_path_rank(H, s, vasp_nodes)
        is_obf = obfuscated_flags[s]
        (sp_top1_mixer if is_obf else sp_top1_direct).append(top1(ranked, ground_truth[s]))
        (sp_top3_mixer if is_obf else sp_top3_direct).append(top3(ranked, ground_truth[s]))
        (sp_mrr_mixer if is_obf else sp_mrr_direct).append(mrr(ranked, ground_truth[s]))

    L, idx, nodelist = build_laplacian(G)
    n = L.shape[0]
    lu = factorize_laplacian(L)
    er_top1_mixer, er_top1_direct = [], []
    er_top3_mixer, er_top3_direct = [], []
    er_mrr_mixer, er_mrr_direct = [], []
    for s in suspects:
        ranked, _ = effective_resistance_rank(s, vasp_nodes, lu, idx, n)
        is_obf = obfuscated_flags[s]
        (er_top1_mixer if is_obf else er_top1_direct).append(top1(ranked, ground_truth[s]))
        (er_top3_mixer if is_obf else er_top3_direct).append(top3(ranked, ground_truth[s]))
        (er_mrr_mixer if is_obf else er_mrr_direct).append(mrr(ranked, ground_truth[s]))

    return {
        "seed": seed,
        "sp_mixer": np.mean(sp_top1_mixer), "sp_direct": np.mean(sp_top1_direct),
        "er_mixer": np.mean(er_top1_mixer), "er_direct": np.mean(er_top1_direct),
        "sp_top3_mixer": np.mean(sp_top3_mixer), "sp_top3_direct": np.mean(sp_top3_direct),
        "er_top3_mixer": np.mean(er_top3_mixer), "er_top3_direct": np.mean(er_top3_direct),
        "sp_mrr_mixer": np.mean(sp_mrr_mixer), "sp_mrr_direct": np.mean(sp_mrr_direct),
        "er_mrr_mixer": np.mean(er_mrr_mixer), "er_mrr_direct": np.mean(er_mrr_direct),
        "n_mixer": len(sp_top1_mixer),
        "sp_mixer_raw": sp_top1_mixer, "er_mixer_raw": er_top1_mixer,
    }

def mcnemar_test(sp_raw, er_raw):
    """Paired test: among mixer cases, how often does ER get it right while SP
    gets it wrong, vs the reverse? This is the correct test for paired
    binary outcomes on the SAME suspects (not independent samples)."""
    sp_raw = np.array(sp_raw)
    er_raw = np.array(er_raw)
    er_right_sp_wrong = np.sum((er_raw == 1) & (sp_raw == 0))
    sp_right_er_wrong = np.sum((sp_raw == 1) & (er_raw == 0))
    both_right = np.sum((sp_raw == 1) & (er_raw == 1))
    both_wrong = np.sum((sp_raw == 0) & (er_raw == 0))
    # McNemar's chi-square (with continuity correction)
    b, c = er_right_sp_wrong, sp_right_er_wrong
    if b + c == 0:
        chi2 = 0.0
    else:
        chi2 = (abs(b - c) - 1) ** 2 / (b + c)
    from scipy.stats import chi2 as chi2_dist
    p_value = 1 - chi2_dist.cdf(chi2, df=1)
    return {
        "ER_right_SP_wrong": int(er_right_sp_wrong),
        "SP_right_ER_wrong": int(sp_right_er_wrong),
        "both_right": int(both_right),
        "both_wrong": int(both_wrong),
        "mcnemar_chi2": chi2,
        "p_value": p_value,
    }


if __name__ == "__main__":
    print("Running across 5 different random seeds to check this isn't a lucky draw...\n")
    seeds = [1, 2, 3, 4, 5]
    results = [run_seed(s) for s in seeds]

    print(f"{'Seed':>6} {'SP-Top1 (Mix)':>15} {'ER-Top1 (Mix)':>15} {'SP-Top3 (Mix)':>15} {'ER-Top3 (Mix)':>15} {'SP-MRR (Mix)':>15} {'ER-MRR (Mix)':>15}")
    for r in results:
        print(f"{r['seed']:>6} {r['sp_mixer']:>15.3f} {r['er_mixer']:>15.3f} {r['sp_top3_mixer']:>15.3f} {r['er_top3_mixer']:>15.3f} {r['sp_mrr_mixer']:>15.3f} {r['er_mrr_mixer']:>15.3f}")

    print("\n--- Direct (Easy) Cases ---")
    print(f"{'Seed':>6} {'SP-Top1 (Dir)':>15} {'ER-Top1 (Dir)':>15} {'SP-Top3 (Dir)':>15} {'ER-Top3 (Dir)':>15} {'SP-MRR (Dir)':>15} {'ER-MRR (Dir)':>15}")
    for r in results:
        print(f"{r['seed']:>6} {r['sp_direct']:>15.3f} {r['er_direct']:>15.3f} {r['sp_top3_direct']:>15.3f} {r['er_top3_direct']:>15.3f} {r['sp_mrr_direct']:>15.3f} {r['er_mrr_direct']:>15.3f}")

    def summary_stats(key):
        vals = [r[key] for r in results]
        return f"{np.mean(vals):.3f} ± {np.std(vals):.3f}"

    print(f"\nMean ± Std on MIXER-routed cases across 5 seeds:")
    print(f"  SP : Top1={summary_stats('sp_mixer')}, Top3={summary_stats('sp_top3_mixer')}, MRR={summary_stats('sp_mrr_mixer')}")
    print(f"  ER : Top1={summary_stats('er_mixer')}, Top3={summary_stats('er_top3_mixer')}, MRR={summary_stats('er_mrr_mixer')}")

    print(f"\nMean ± Std on DIRECT cases across 5 seeds:")
    print(f"  SP : Top1={summary_stats('sp_direct')}, Top3={summary_stats('sp_top3_direct')}, MRR={summary_stats('sp_mrr_direct')}")
    print(f"  ER : Top1={summary_stats('er_direct')}, Top3={summary_stats('er_top3_direct')}, MRR={summary_stats('er_mrr_direct')}")

    gaps = [r['er_mixer'] - r['sp_mixer'] for r in results]
    print(f"\nMean gap (ER - SP Top1) on mixer-routed cases across 5 seeds: {np.mean(gaps):+.3f}  (std: {np.std(gaps):.3f})")

    print("\n--- Paired significance test (McNemar) on seed=42 run for a concrete p-value ---")
    r42 = run_seed(42)
    mc = mcnemar_test(r42['sp_mixer_raw'], r42['er_mixer_raw'])
    print(mc)
