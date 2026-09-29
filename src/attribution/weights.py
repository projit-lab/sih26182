import math
import networkx as nx

def _log_scale_weights(G: nx.Graph) -> nx.Graph:
    """Replace raw-BTC edge weights with log1p(amount_satoshis) conductance.
    See docs/ENGINE_CODE_REVIEW.md Improvement A: raw amounts gave ~208x
    worse Laplacian conditioning on heavy-tailed real transaction data."""
    for u, v, data in G.edges(data=True):
        sats = data.get("amount_satoshis")
        if sats is not None:
            data["weight"] = math.log1p(float(sats))
    return G
