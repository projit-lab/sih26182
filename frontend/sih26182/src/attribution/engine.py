"""
Core attribution engine: given a suspect wallet and a set of candidate VASPs,
rank candidates by effective resistance on the transaction graph.

This is the production version of the validated logic -- same math as the
validation experiments, cleaned up for reuse (factorize once, query many times).
"""
from dataclasses import dataclass
import networkx as nx
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


@dataclass
class AttributionResult:
    suspect: str
    ranked_candidates: list       # best guess first
    scores: dict                  # candidate -> effective resistance (lower = more likely source)
    method: str = "effective_resistance"


class AttributionEngine:
    """
    Wraps a transaction graph (networkx, weighted by tx amount/frequency) and
    exposes wallet -> ranked-VASP-candidates attribution via effective resistance.

    Usage:
        engine = AttributionEngine(graph)
        result = engine.attribute("suspect_wallet_123", ["VASP_A", "VASP_B", ...])
    """

    def __init__(self, graph: nx.Graph, weight_attr: str = "weight"):
        self.graph = graph
        self.weight_attr = weight_attr
        self._nodes = list(graph.nodes())
        self._idx = {n: i for i, n in enumerate(self._nodes)}
        self._n = len(self._nodes)
        self._lu = None  # lazy factorization

    def _factorize(self):
        """Factorize the grounded Laplacian once. Reused across all queries --
        this is what makes the method fast enough for real-time use."""
        L = nx.laplacian_matrix(self.graph, nodelist=self._nodes, weight=self.weight_attr).astype(float)
        n = L.shape[0]
        # ground node 0 to remove null space (standard trick, avoids full pseudoinverse)
        L_grounded = L[1:, :][:, 1:] + sp.eye(n - 1) * 1e-10
        self._lu = spla.splu(L_grounded.tocsc())

    def _resistance(self, source_idx: int, target_idx: int) -> float:
        n = self._n
        b = np.zeros(n - 1)
        if source_idx != 0:
            b[source_idx - 1] += 1.0
        if target_idx != 0:
            b[target_idx - 1] -= 1.0
        x = self._lu.solve(b)
        xs = 0.0 if source_idx == 0 else x[source_idx - 1]
        xt = 0.0 if target_idx == 0 else x[target_idx - 1]
        return abs(xs - xt)

    def attribute(self, suspect: str, candidates: list) -> AttributionResult:
        if self._lu is None:
            self._factorize()
        if suspect not in self._idx:
            raise ValueError(f"Suspect wallet '{suspect}' not found in graph")

        s_idx = self._idx[suspect]
        scores = {}
        for c in candidates:
            if c not in self._idx:
                scores[c] = float("inf")
                continue
            scores[c] = self._resistance(s_idx, self._idx[c])

        ranked = sorted(candidates, key=lambda c: scores[c])
        return AttributionResult(suspect=suspect, ranked_candidates=ranked, scores=scores)

    def attribute_batch(self, suspects: list, candidates: list) -> list:
        """Attribute many suspects against the same candidate pool. Factorizes
        once, then reuses -- this is the realistic deployment pattern."""
        if self._lu is None:
            self._factorize()
        return [self.attribute(s, candidates) for s in suspects]
