"""
Silk Road Dedicated Forensic Attribution Engine
Isolated implementation of the Grounded Laplacian Linear Solver (Lx = b).

Mathematically models the Bitcoin multi-hop laundering graph as an electrical resistive
network to rank candidate destination VASPs by effective resistance (R_eff).
Zero dependencies on or modifications to the primary platform engine.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import networkx as nx
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


@dataclass
class SilkRoadVaspRanking:
    vasp_name: str
    address: str
    effective_resistance: float
    conductance: float
    confidence_score: float
    category: str = "exchange"


@dataclass
class SilkRoadAttributionResult:
    suspect_address: str
    ranked_vasps: List[SilkRoadVaspRanking]
    compute_time_ms: float
    graph_nodes: int
    graph_edges: int
    solver_method: str = "Dirichlet_Grounded_Laplacian_LU"


class SilkRoadAttributionEngine:
    """
    Independent attribution solver for Silk Road on-chain laundering graphs.
    Solves Lx = b on the weighted conductance graph and calculates effective resistance:
        R_eff(s, t) = |x_s - x_t| where L * x = e_s - e_t
    """

    def __init__(self, graph: nx.Graph, weight_attr: str = "weight"):
        self.graph = graph
        self.weight_attr = weight_attr
        self._nodes = list(graph.nodes())
        self._idx = {n: i for i, n in enumerate(self._nodes)}
        self._n = len(self._nodes)
        self._lu = None

    def _factorize(self):
        """
        Constructs the Laplacian matrix L and factorizes the grounded submatrix.
        Grounds node 0 to eliminate the null space of constant vectors.
        """
        L = nx.laplacian_matrix(self.graph, nodelist=self._nodes, weight=self.weight_attr).astype(float)
        n = L.shape[0]
        if n <= 1:
            raise ValueError("Graph must contain at least 2 connected nodes to solve Laplacian.")

        # Ground reference node 0 and add regularizer for numerical stability
        L_grounded = L[1:, :][:, 1:] + sp.eye(n - 1) * 1e-10
        self._lu = spla.splu(L_grounded.tocsc())

    def compute_effective_resistance(self, source_addr: str, target_addr: str) -> float:
        """
        Solves Lx = b for unit current injected at source and extracted at target.
        """
        if self._lu is None:
            self._factorize()

        s_idx = self._idx.get(source_addr)
        t_idx = self._idx.get(target_addr)

        if s_idx is None or t_idx is None:
            return float("inf")
        if s_idx == t_idx:
            return 0.0

        n = self._n
        b = np.zeros(n - 1)
        if s_idx != 0:
            b[s_idx - 1] += 1.0
        if t_idx != 0:
            b[t_idx - 1] -= 1.0

        x = self._lu.solve(b)
        xs = 0.0 if s_idx == 0 else x[s_idx - 1]
        xt = 0.0 if t_idx == 0 else x[t_idx - 1]

        return float(abs(xs - xt))

    def attribute(
        self,
        suspect_address: str,
        candidate_vasps: Dict[str, str],  # address -> VASP Name
    ) -> SilkRoadAttributionResult:
        """
        Attributes a suspect wallet against candidate VASP target addresses.
        Normalizes inverse resistances into a rigorous probabilistic confidence distribution.
        """
        import time
        t0 = time.perf_counter()

        if suspect_address not in self._idx:
            raise ValueError(f"Suspect address '{suspect_address}' not present in Silk Road graph.")

        results: List[SilkRoadVaspRanking] = []
        resistances: Dict[str, float] = {}

        for addr, name in candidate_vasps.items():
            if addr in self._idx:
                r_eff = self.compute_effective_resistance(suspect_address, addr)
            else:
                r_eff = float("inf")
            resistances[addr] = r_eff

        # Filter finite candidates
        finite = {k: v for k, v in resistances.items() if not np.isinf(v) and v > 0}

        if finite:
            # Conductance C_i = 1 / R_eff_i
            total_conductance = sum(1.0 / r for r in finite.values())
            for addr, name in candidate_vasps.items():
                r = resistances.get(addr, float("inf"))
                if addr in finite:
                    cond = 1.0 / r
                    conf = cond / total_conductance
                else:
                    cond = 0.0
                    conf = 0.0

                results.append(
                    SilkRoadVaspRanking(
                        vasp_name=name,
                        address=addr,
                        effective_resistance=round(r, 6),
                        conductance=round(cond, 6),
                        confidence_score=round(conf, 4),
                    )
                )
        else:
            for addr, name in candidate_vasps.items():
                results.append(
                    SilkRoadVaspRanking(
                        vasp_name=name,
                        address=addr,
                        effective_resistance=float("inf"),
                        conductance=0.0,
                        confidence_score=0.0,
                    )
                )

        # Sort by lowest effective resistance (highest confidence first)
        results.sort(key=lambda item: item.effective_resistance)

        elapsed = round((time.perf_counter() - t0) * 1000, 2)

        return SilkRoadAttributionResult(
            suspect_address=suspect_address,
            ranked_vasps=results,
            compute_time_ms=elapsed,
            graph_nodes=self.graph.number_of_nodes(),
            graph_edges=self.graph.number_of_edges(),
        )
