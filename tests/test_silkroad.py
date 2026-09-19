"""
Unit Test: Silk Road Dedicated Forensic Attribution ($Lx = b$)
Validates that the dedicated Silk Road engine ranks Coinbase Prime Custody #1
with lowest effective resistance over Kraken and Binance.
"""
import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import networkx as nx
from silkroad.engine import SilkRoadAttributionEngine
from silkroad.loader import build_silkroad_graph


def test_silkroad_dedicated_engine():
    """
    Validates that SilkRoadAttributionEngine computes R_eff correctly and
    ranks Coinbase Prime Custody #1.
    """
    G, candidate_vasps = build_silkroad_graph()
    engine = SilkRoadAttributionEngine(G)

    suspect = "1F1tAaz5x1HUXrCNLbtMDqcw6o5GNn4xqX"
    res = engine.attribute(suspect, candidate_vasps)

    assert len(res.ranked_vasps) >= 3, "Expected at least 3 ranked candidate VASPs"
    top = res.ranked_vasps[0]
    assert "Coinbase" in top.vasp_name, f"Expected Coinbase Prime #1, got {top.vasp_name}"

    # Verify resistance ordering: Coinbase < Kraken < Binance
    r_map = {item.vasp_name: item.effective_resistance for item in res.ranked_vasps}
    assert r_map["Coinbase Prime Custody"] < r_map["Kraken"] < r_map["Binance"], (
        f"Resistance ordering mismatch: {r_map}"
    )

    print(f"PASS: Silk Road dedicated engine verified! Top VASP: {top.vasp_name} ({top.confidence_score * 100:.1f}%)")


if __name__ == "__main__":
    test_silkroad_dedicated_engine()
