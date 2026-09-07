"""
Demo Dedicated Forensic Attribution Engine
Implements:
1. Dirichlet Grounded Laplacian Linear Solver (Lx = b) using Circuit Theory (Ohm's Law)
2. Classical Shortest-Path (Dijkstra) solver for side-by-side scientific comparison
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
import networkx as nx
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
import time


@dataclass
class DemoVaspRanking:
    vasp_name: str
    address: str
    effective_resistance: float
    conductance: float
    confidence_score: float
    hop_distance: int
    flow_btc: float
    category: str = "exchange"


@dataclass
class DemoAttributionResult:
    suspect_address: str
    ranked_vasps: List[DemoVaspRanking]
    compute_time_ms: float
    graph_nodes: int
    graph_edges: int
    dijkstra_winner: str
    dijkstra_hop_count: int
    solver_method: str = "Dirichlet_Grounded_Laplacian_LU"


class DemoAttributionEngine:
    """
    Independent attribution solver for 4-6 hop asymmetric laundering graphs.
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
        L = nx.laplacian_matrix(self.graph, nodelist=self._nodes, weight=self.weight_attr).astype(float)
        n = L.shape[0]
        if n <= 1:
            raise ValueError("Graph must contain at least 2 connected nodes to solve Laplacian.")

        # Ground node 0 with regularizer for numerical stability
        L_grounded = L[1:, :][:, 1:] + sp.eye(n - 1) * 1e-10
        self._lu = spla.splu(L_grounded.tocsc())

    def compute_effective_resistance(self, source_addr: str, target_addr: str) -> float:
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

    def run_dijkstra(self, suspect_address: str, candidate_vasps: Dict[str, str]) -> tuple[str, int]:
        """Calculates traditional shortest path (hop count) to candidate VASPs."""
        shortest_len = float("inf")
        winner = None
        for addr in candidate_vasps:
            try:
                length = nx.shortest_path_length(self.graph, source=suspect_address, target=addr)
                if length < shortest_len:
                    shortest_len = length
                    winner = addr
            except nx.NetworkXNoPath:
                continue
        return winner, int(shortest_len) if winner else 0

    def attribute(
        self,
        suspect_address: str,
        candidate_vasps: Dict[str, str],
    ) -> DemoAttributionResult:
        t0 = time.perf_counter()

        if suspect_address not in self.graph:
            raise ValueError(f"Suspect address '{suspect_address}' not present in graph.")

        # Isolate connected component for suspect
        if not nx.is_connected(self.graph):
            comp_nodes = nx.node_connected_component(self.graph, suspect_address)
            active_graph = self.graph.subgraph(comp_nodes).copy()
        else:
            active_graph = self.graph

        self._nodes = list(active_graph.nodes())
        self._idx = {n: i for i, n in enumerate(self._nodes)}
        self._n = len(self._nodes)
        self._lu = None

        results: List[DemoVaspRanking] = []
        resistances: Dict[str, float] = {}

        for addr, name in candidate_vasps.items():
            if addr in self._idx:
                r_eff = self.compute_effective_resistance(suspect_address, addr)
            else:
                r_eff = float("inf")
            resistances[addr] = r_eff

        finite = {k: v for k, v in resistances.items() if not np.isinf(v) and v > 0}
        total_conductance = sum(1.0 / r for r in finite.values()) if finite else 1.0

        for addr, name in candidate_vasps.items():
            r = resistances.get(addr, float("inf"))
            cond = (1.0 / r) if addr in finite else 0.0
            conf = (cond / total_conductance) if addr in finite else 0.0

            # Find hop distance
            try:
                hops = nx.shortest_path_length(self.graph, source=suspect_address, target=addr)
            except Exception:
                hops = -1

            # Find flow BTC to this node
            in_sats = sum(self.graph[u][addr].get("amount_satoshis", 0) for u in self.graph.predecessors(addr)) if self.graph.is_directed() else sum(self.graph[u][addr].get("amount_satoshis", 0) for u in self.graph.neighbors(addr))
            flow_btc = in_sats / 1e8

            results.append(
                DemoVaspRanking(
                    vasp_name=name,
                    address=addr,
                    effective_resistance=round(r, 6),
                    conductance=round(cond, 6),
                    confidence_score=round(conf, 4),
                    hop_distance=hops,
                    flow_btc=flow_btc,
                )
            )

        results.sort(key=lambda item: item.effective_resistance)
        elapsed = round((time.perf_counter() - t0) * 1000, 2)

        # Run Dijkstra comparison
        dijkstra_winner, dijkstra_hops = self.run_dijkstra(suspect_address, candidate_vasps)

        return DemoAttributionResult(
            suspect_address=suspect_address,
            ranked_vasps=results,
            compute_time_ms=elapsed,
            graph_nodes=self.graph.number_of_nodes(),
            graph_edges=self.graph.number_of_edges(),
            dijkstra_winner=candidate_vasps.get(dijkstra_winner, "None"),
            dijkstra_hop_count=dijkstra_hops,
        )
