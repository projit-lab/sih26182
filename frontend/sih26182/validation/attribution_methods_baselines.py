"""
Three competing methods for: given a suspect wallet, rank the candidate VASPs
by how likely each is to be the TRUE source, using only graph structure/weights.

1. shortest_path_rank   -- the "obvious" baseline (weighted shortest path / geodesic)
2. effective_resistance_rank -- our hypothesis (circuit-theory / Laplacian pseudoinverse)
3. graphsage_rank -- a real trained GraphSAGE (torch_geometric), using proximity of
   learned embeddings between suspect and VASP nodes as the ranking score.

All three output, for each suspect, a ranked list of VASP candidates
(best guess first). We then score each method by:
  - Top-1 accuracy (did the #1 ranked VASP match ground truth?)
  - Mean Reciprocal Rank (MRR) -- rewards getting the true VASP ranked highly
    even if not #1.
"""

import networkx as nx
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


# ---------------------------------------------------------------------------
# Method 1: Weighted shortest path (treat weight as "connection strength" ->
# convert to a cost by inverting it, since higher tx weight/frequency should
# mean a "cheaper"/more traversable path in a tracing sense).
# ---------------------------------------------------------------------------
def prepare_shortest_path_graph(G):
    """Precompute a 'length' edge attribute (1/weight) once, so per-suspect
    queries are a single fast Dijkstra call instead of N slow lambda-weighted
    per-pair calls."""
    H = G.copy()
    for u, v, d in H.edges(data=True):
        d['length'] = 1.0 / d['weight']
    return H


def shortest_path_rank(H, suspect, vasp_nodes):
    # single_source Dijkstra ONCE per suspect (not once per suspect-VASP pair)
    lengths_all = nx.single_source_dijkstra_path_length(H, suspect, weight='length')
    lengths = {v: lengths_all.get(v, float('inf')) for v in vasp_nodes}
    ranked = sorted(vasp_nodes, key=lambda v: lengths[v])
    return ranked, lengths


# ---------------------------------------------------------------------------
# Method 2: Effective resistance via Laplacian pseudoinverse.
# For a graph this size (~3.5k nodes) exact pseudoinverse via sparse linear
# solve per query is feasible (this is the "local algorithm" style: solve
# L x = e_i - e_j for each candidate pair using a sparse solver, not the full
# dense pseudoinverse matrix -- this is what scales in practice, per the
# Spielman-Srivastava / local-solver literature).
# ---------------------------------------------------------------------------
def build_laplacian(G):
    nodes = list(G.nodes())
    idx = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)
    L = nx.laplacian_matrix(G, nodelist=nodes, weight='weight').astype(float)
    return L.tocsc(), idx, nodes


def factorize_laplacian(L):
    """Factorize the (regularized, grounded) Laplacian ONCE. Reused across all
    suspect/VASP queries -- this is what makes effective-resistance tractable
    at scale (matches the 'local solver' literature: one factorization,
    many fast triangular back-substitutions, instead of a full O(n^3) dense
    pseudoinverse)."""
    n = L.shape[0]
    # Ground the system by fixing node 0's potential to 0 (removes the null
    # space from the all-ones vector) -- standard trick, equivalent to the
    # pseudoinverse approach but much cheaper to factorize.
    L_grounded = L[1:, :][:, 1:] + sp.eye(n - 1) * 1e-10
    lu = spla.splu(L_grounded.tocsc())
    return lu


def effective_resistance_rank(suspect, vasp_nodes, lu, idx, n):
    s_idx = idx[suspect]

    def solve_for(target_idx):
        b = np.zeros(n - 1)
        # grounded index shift: node 0 is removed from the system
        if s_idx != 0:
            b[s_idx - 1] += 1.0
        if target_idx != 0:
            b[target_idx - 1] -= 1.0
        x = lu.solve(b)
        # potential at s minus potential at target = effective resistance
        xs = 0.0 if s_idx == 0 else x[s_idx - 1]
        xt = 0.0 if target_idx == 0 else x[target_idx - 1]
        return abs(xs - xt)

    resistances = {}
    for v in vasp_nodes:
        v_idx = idx[v]
        resistances[v] = solve_for(v_idx)

    ranked = sorted(vasp_nodes, key=lambda v: resistances[v])
    return ranked, resistances


# ---------------------------------------------------------------------------
# Method 3: Real GraphSAGE (torch_geometric), unsupervised-ish setup:
# train embeddings using a link-prediction style objective (predict which
# edges exist), then rank VASP candidates for each suspect by embedding
# cosine similarity. This mirrors how a GraphSAGE-based tracing tool would
# actually be used in practice (learned proximity in embedding space).
# ---------------------------------------------------------------------------
def graphsage_rank_all(G, suspects, vasp_nodes, embedding_dim=32, epochs=150, seed=0):
    import torch
    import torch.nn.functional as F
    from torch_geometric.utils import from_networkx
    from torch_geometric.nn import SAGEConv

    torch.manual_seed(seed)

    nodes = list(G.nodes())
    idx = {n: i for i, n in enumerate(nodes)}

    # Build PyG data object. No node features exist in this synthetic graph
    # (mirrors real-world where wallet "features" are often thin/unreliable) --
    # so we use learnable embeddings as input, which is standard practice
    # for graphs without rich node features.
    data = from_networkx(G)
    num_nodes = data.num_nodes

    class GraphSAGEEmbed(torch.nn.Module):
        def __init__(self, num_nodes, emb_dim, hidden_dim=32):
            super().__init__()
            self.embed = torch.nn.Embedding(num_nodes, emb_dim)
            self.conv1 = SAGEConv(emb_dim, hidden_dim)
            self.conv2 = SAGEConv(hidden_dim, hidden_dim)

        def forward(self, edge_index):
            x = self.embed.weight
            x = self.conv1(x, edge_index)
            x = F.relu(x)
            x = self.conv2(x, edge_index)
            return x

    model = GraphSAGEEmbed(num_nodes, embedding_dim)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

    edge_index = data.edge_index

    # simple negative sampling link-prediction training loop
    def sample_negative_edges(num_nodes, num_samples):
        return torch.randint(0, num_nodes, (2, num_samples))

    num_pos = edge_index.shape[1]

    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        z = model(edge_index)

        pos_src, pos_dst = edge_index
        pos_score = (z[pos_src] * z[pos_dst]).sum(dim=1)

        neg_edges = sample_negative_edges(num_nodes, num_pos)
        neg_src, neg_dst = neg_edges
        neg_score = (z[neg_src] * z[neg_dst]).sum(dim=1)

        pos_loss = F.binary_cross_entropy_with_logits(pos_score, torch.ones_like(pos_score))
        neg_loss = F.binary_cross_entropy_with_logits(neg_score, torch.zeros_like(neg_score))
        loss = pos_loss + neg_loss
        loss.backward()
        optimizer.step()

    model.eval()
    with torch.no_grad():
        z = model(edge_index).numpy()

    # rank VASPs for every suspect by cosine similarity of learned embeddings
    def cos(a, b):
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

    results = {}
    for s in suspects:
        s_vec = z[idx[s]]
        sims = {v: cos(s_vec, z[idx[v]]) for v in vasp_nodes}
        ranked = sorted(vasp_nodes, key=lambda v: -sims[v])  # higher similarity = better
        results[s] = (ranked, sims)

    return results, float(loss.item())
