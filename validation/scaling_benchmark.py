import time
import tracemalloc
import networkx as nx
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
import platform
import sys

import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.attribution.engine import AttributionEngine
from src.attribution.weights import _log_scale_weights

def benchmark_n(N):
    print(f"\n--- Benchmarking N={N} ---")
    np.random.seed(42)
    G = nx.barabasi_albert_graph(N, 2, seed=N)
    
    for u, v in G.edges():
        G[u][v]["amount_satoshis"] = np.random.lognormal(mean=5.0, sigma=2.0)
        
    G = _log_scale_weights(G)
    nodes = list(G.nodes())
    
    # Repetitions
    reps = 3
    fact_times = []
    query_times = []
    cg_query_times = []
    
    for _ in range(reps):
        tracemalloc.start()
        engine = AttributionEngine(G)
        
        t0 = time.time()
        engine._factorize()
        t_fact = time.time() - t0
        fact_times.append(t_fact)
        
        # queries
        qt = []
        for _ in range(50):
            suspect = np.random.choice(nodes)
            cands = list(np.random.choice(nodes, size=5, replace=False))
            t1 = time.time()
            engine.attribute(suspect, cands)
            qt.append(time.time() - t1)
        query_times.append(np.mean(qt))
        
        # Memory
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
    # CG
    try:
        L = nx.laplacian_matrix(G, weight="weight").astype(float)
        L_grounded = (L[1:, :][:, 1:] + sp.eye(N - 1) * 1e-6).tocsc()
        diag = L_grounded.diagonal()
        M = sp.diags(1.0 / diag)
        
        cg_qt = []
        for _ in range(50):
            suspect = np.random.randint(0, N)
            cands = np.random.randint(0, N, size=5)
            
            t1 = time.time()
            for cand in cands:
                b = np.zeros(N - 1)
                if suspect != 0: b[suspect - 1] += 1
                if cand != 0: b[cand - 1] -= 1
                x, info = spla.cg(L_grounded, b, M=M, rtol=1e-5)
            cg_qt.append((time.time() - t1))
        cg_query_times.append(np.mean(cg_qt))
    except Exception as e:
        print(f"CG failed: {e}")
        
    med_fact = np.median(fact_times)
    med_q = np.median(query_times) * 1000
    cg_med_q = np.median(cg_query_times) * 1000 if cg_query_times else float('nan')
    peak_mb = peak / 1024 / 1024
    
    print(f"N={N}: factorize={med_fact:.4f}s, query={med_q:.2f}ms, cg_query={cg_med_q:.2f}ms, peak_mem={peak_mb:.1f}MB")
    return {
        "N": N,
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "fact": med_fact,
        "query": med_q,
        "cg": cg_med_q,
        "peak_mb": peak_mb
    }

def main():
    Ns = [200, 2000, 20000]
    results = []
    
    total_time_20k = 0
    for N in Ns:
        t0 = time.time()
        res = benchmark_n(N)
        results.append(res)
        if N == 20000:
            total_time_20k = time.time() - t0
            
    if total_time_20k < 60:
        results.append(benchmark_n(200000))
        
    out = "# Attribution Engine Scaling\n\n"
    out += "| N | nodes | edges | factorize s | per-query ms | peak MB | CG per-query ms |\n"
    out += "|---|-------|-------|-------------|--------------|---------|-----------------|\n"
    for r in results:
        out += f"| {r['N']} | {r['nodes']} | {r['edges']} | {r['fact']:.4f} | {r['query']:.2f} | {r['peak_mb']:.1f} | {r['cg']:.2f} |\n"
        
    out += "\n## System Info\n"
    out += f"- CPU: {platform.processor()}\n"
    out += f"- Python: {platform.python_version()}\n"
    out += f"- NumPy: {np.__version__}\n"
    import scipy
    out += f"- SciPy: {scipy.__version__}\n"
    out += f"- NetworkX: {nx.__version__}\n"
    
    with open("docs/results/scaling.md", "w") as f:
        f.write(out)
        
    print("\n" + out)

if __name__ == "__main__":
    main()
