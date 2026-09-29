"""
Synthetic wallet-transaction graph generator for testing:
  Effective Resistance  vs  Shortest Path  vs  GraphSAGE
on the task: "attribute a downstream wallet back to its true source VASP,
after funds have passed through obfuscation layers (mixers / fan-out-fan-in)."

Design principles (kept honest, not rigged):
- Multiple TRUE sources (VASPs) exist simultaneously in the graph, each with
  its own legitimate-looking transaction fan-out into the general population.
- A SUBSET of source->destination flows are routed through "mixer" nodes that
  deliberately fragment a single flow into many redundant weak parallel paths
  (this is the actual real-world obfuscation pattern we're testing robustness to).
- Plenty of unrelated background traffic (noise wallets transacting with each
  other) is added so the true path is not the only thing in the graph.
- Ground truth (which source each downstream "suspect" wallet truly traces to)
  is recorded at generation time, BEFORE any obfuscation-aware method sees it.
"""

import networkx as nx
import numpy as np
import random

def generate_graph(
    n_background_wallets=2500,
    n_vasps=6,
    n_suspects=180,
    mixer_fraction=0.6,      # fraction of source->suspect flows routed through a mixer
    mixer_fanout=(4, 9),     # mixer splits a flow into this many parallel hops
    background_edges_per_node=3,
    seed=42,
):
    rng = random.Random(seed)
    np.random.seed(seed)

    G = nx.Graph()  # undirected weighted graph; weight = "conductance" (higher = stronger/more frequent flow)

    # --- 1. Background population (noise wallets) ---
    bg_nodes = [f"bg_{i}" for i in range(n_background_wallets)]
    G.add_nodes_from(bg_nodes, kind="background")

    # random sparse background traffic (Barabasi-Albert-ish via random attachment for realism)
    for i, node in enumerate(bg_nodes):
        for _ in range(background_edges_per_node):
            other = rng.choice(bg_nodes)
            if other != node:
                w = np.random.lognormal(mean=0.0, sigma=1.0)  # skewed tx-volume-like weight
                if G.has_edge(node, other):
                    G[node][other]['weight'] += w
                else:
                    G.add_edge(node, other, weight=w)

    # --- 2. VASP (source) nodes ---
    vasp_nodes = [f"VASP_{v}" for v in range(n_vasps)]
    G.add_nodes_from(vasp_nodes, kind="vasp")
    # each VASP also has some legitimate ordinary traffic with background wallets (realism / red herrings)
    for v in vasp_nodes:
        for _ in range(15):
            other = rng.choice(bg_nodes)
            w = np.random.lognormal(mean=0.5, sigma=1.0)
            if G.has_edge(v, other):
                G[v][other]['weight'] += w
            else:
                G.add_edge(v, other, weight=w)

    # --- 3. Suspect nodes with GROUND TRUTH source, some routed through mixers ---
    suspect_nodes = [f"suspect_{i}" for i in range(n_suspects)]
    G.add_nodes_from(suspect_nodes, kind="suspect")

    ground_truth = {}  # suspect -> true source VASP

    mixer_counter = 0
    for i, s in enumerate(suspect_nodes):
        true_vasp = rng.choice(vasp_nodes)
        ground_truth[s] = true_vasp

        if rng.random() < mixer_fraction:
            # ---- OBFUSCATED PATH: fragment the flow across several parallel mixer hops ----
            k = rng.randint(*mixer_fanout)
            mixer_hop_nodes = []
            for j in range(k):
                m = f"mixer_{mixer_counter}"
                mixer_counter += 1
                G.add_node(m, kind="mixer")
                mixer_hop_nodes.append(m)
                # VASP -> mixer hop (weak individual edge, deliberately fragmented)
                w1 = np.random.lognormal(mean=-0.5, sigma=0.6)  # weaker than a direct path
                G.add_edge(true_vasp, m, weight=w1)
                # mixer hop -> suspect (also weak)
                w2 = np.random.lognormal(mean=-0.5, sigma=0.6)
                G.add_edge(m, s, weight=w2)
                # mixer hop also connects to random background noise (to look "generic")
                for _ in range(2):
                    bgnode = rng.choice(bg_nodes)
                    w3 = np.random.lognormal(mean=-0.2, sigma=0.8)
                    if G.has_edge(m, bgnode):
                        G[m][bgnode]['weight'] += w3
                    else:
                        G.add_edge(m, bgnode, weight=w3)
            # ALSO add a few decoy mixer paths to OTHER vasps at low weight (real mixers
            # commingle funds from many depositors -- this is what makes tracing hard)
            for _ in range(rng.randint(1, 3)):
                decoy_vasp = rng.choice([v for v in vasp_nodes if v != true_vasp])
                decoy_mixer = rng.choice(mixer_hop_nodes)
                w = np.random.lognormal(mean=-1.0, sigma=0.5)
                G.add_edge(decoy_vasp, decoy_mixer, weight=w)
        else:
            # ---- DIRECT / lightly-obfuscated path (a couple of hops, no fragmentation) ----
            hop = f"hop_{i}"
            G.add_node(hop, kind="hop")
            w1 = np.random.lognormal(mean=0.3, sigma=0.5)
            w2 = np.random.lognormal(mean=0.3, sigma=0.5)
            G.add_edge(true_vasp, hop, weight=w1)
            G.add_edge(hop, s, weight=w2)

        # every suspect also has a little background noise traffic (realism)
        for _ in range(2):
            other = rng.choice(bg_nodes)
            w = np.random.lognormal(mean=-0.3, sigma=0.7)
            if G.has_edge(s, other):
                G[s][other]['weight'] += w
            else:
                G.add_edge(s, other, weight=w)

    return G, vasp_nodes, suspect_nodes, ground_truth


if __name__ == "__main__":
    G, vasps, suspects, gt = generate_graph()
    print(f"Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")
    print(f"VASPs: {len(vasps)}, Suspects: {len(suspects)}")
    kinds = {}
    for n, d in G.nodes(data=True):
        kinds[d.get('kind')] = kinds.get(d.get('kind'), 0) + 1
    print("Node kinds:", kinds)
    print("Sample ground truth:", list(gt.items())[:5])
