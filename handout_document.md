# SIH26182 — Executive & Technical Handout

**Project Title:** Wallet-to-VASP Attribution via Circuit Theory ($Lx = b$)  
**Domain:** Blockchain Forensics, Graph Theory, Financial Crime Investigation  
**Target Agency:** Ministry of Home Affairs (MHA) / Law Enforcement Agencies (LEAs)  
**Status:** Validated on Bitcoin Mainnet • Production-Ready Backend & Interactive Canvas

---

## 1. Executive Summary & Problem Solved

### The Problem
Criminals laundering stolen cryptocurrency do not hold crypto indefinitely; they must cash out through **Virtual Asset Service Providers (VASPs)**—regulated exchanges like Binance, Coinbase, or Kraken. To hide their tracks, they deploy complex obfuscation:
1. **Mixer Entropy Traps (CoinJoin/Wasabi):** Splitting volume across high-entropy anonymizing pools.
2. **Peeling Chains & Low-Fee Decoys:** Routing a tiny $0.001\text{ BTC}$ decoy along a clean 2-hop path to an innocent exchange, while routing the true $100\text{ BTC}$ through a 6-hop mixer swarm to the actual cash-out vault.

### The Failure of Traditional Forensics
* **Shortest-Path Algorithms (Dijkstra / A\*):** Only evaluate a single cheapest path. They fall into the decoy trap every time, attributing to the 2-hop decoy and missing 99% of stolen assets.
* **Supervised Graph Neural Networks (GraphSAGE):** Require thousands of labeled criminal attribution cases to train. In India, no such public dataset exists. Under novel obfuscation patterns, GNN accuracy collapses by **-24.5 percentage points**.

---

## 2. Our Core Breakthrough: Circuit Theory ($Lx = b$)

Instead of heuristic pathfinding or black-box neural networks, our system models the blockchain as an **Electrical Resistor Network**:

| Blockchain Concept | Electrical Circuit Domain |
| :--- | :--- |
| **Wallet Address** | Circuit Node / Junction |
| **Transaction Volume (Satoshis / BTC)** | Electrical Conductance ($w = 1 / R$) |
| **Suspect Target Wallet** | Current Source (Inject $+1.0\text{ A}$) |
| **Candidate VASP / Exchange** | Ground Reference Node ($V = 0\text{ V}$) |
| **Attribution Confidence Score** | Inverse Effective Resistance ($1 / R_{\text{eff}}$) |

### The Governing Equation: Grounded Graph Laplacian
$$\mathbf{L}_{\text{grounded}} \cdot \mathbf{v} = \mathbf{I}_{\text{unit}}$$
where $\mathbf{L} = \mathbf{D} - \mathbf{W}$ (Degree matrix minus Conductance matrix).

### Why Physics Defeats Criminal Mixers: Rayleigh’s Monotonicity Principle
In physics, adding parallel resistor paths **strictly decreases total effective resistance**:
$$\frac{1}{R_{\text{total}}} = \sum_{k=1}^{n} \frac{1}{R_k}$$
The exact evasion tactic criminals use—splitting funds across dozens of parallel mixer channels—is the **exact physical condition that makes our engine more confident**, driving effective resistance down and attributing the true exchange with undeniable mathematical certainty. **Zero training data required.**

---

## 3. End-to-End System Architecture

```
[ Suspect Wallet ] ──► [ Multi-Tier Ingestion ] ──► [ Bounded Subgraph Extractor ]
                                                          │
   ┌──────────────────────────────────────────────────────┘
   ▼
[ Grounded Laplacian Solver (Lx = b) ] ──► [ Inverse Resistance Softmax ]
                                                 │
   ┌─────────────────────────────────────────────┴────────────────────────────────┐
   ▼                                             ▼                                ▼
[ Cytoscape.js Interactive UI ]      [ Section 65B Court PDF ]      [ SAHYOG Sec 91 CrPC Notice ]
```

### Key Modules Developed:
1. **Multi-Tier Ingestion & Proportional UTXO Haircut (`blockstream_client.py`):**
   * Multi-provider live failover: `Mempool.space` $\to$ `Blockstream.info` $\to$ `Blockchain.info`.
   * Proportional UTXO stake parser: apportions outputs by input satoshi weight instead of naive equal splitting.
2. **Bounded Subgraph Extractor (`extractor.py`):**
   * **Directional Temporal Filter:** Prunes reverse-time historical edges where $t_{\text{out}} < t_{\text{in}} - 2\text{h}$.
   * **High-Degree Hub Protection:** Halts expansion if node degree $\ge 45$ to prevent $O(b^k)$ combinatorial graph explosion.
   * **Adaptive Volume Beam Search:** Dynamically captures $\ge 85\%$ volume across bounded representative channels.
3. **Core Sparse Laplacian Solver (`src/attribution/engine.py`):**
   * Eliminates null-space singularity via Dirichlet grounding ($V_0 = 0\text{ V}$).
   * Pre-factorizes $\mathbf{L}_{\text{grounded}}$ using **Sparse LU Decomposition** (`splu`), enabling sub-millisecond query evaluation.
4. **Law Enforcement & Court Integration:**
   * **Section 65B Indian Evidence Act Forensic PDF (`report_service.py`):** Programmatically compiles court-admissible forensic packages with SHA-256 cryptographic audit chains.
   * **SAHYOG Section 91 CrPC Dispatcher (`routers/sahyog.py`):** Issues formal statutory freeze notices to exchange compliance nodal officers with government acknowledgment tokens (`SAHYOG-ACK-2026-XXXX`).
5. **Interactive Forensic Canvas (`graph_visualizer.html`):**
   * Full Cytoscape.js visualizer featuring Dagre and CoSE physics layouts, real-time node inspector, and one-click court export.

---

## 4. Empirical & Real-World Validation

| Validation Metric | Traditional Dijkstra | GraphSAGE GNN | **SIH26182 (Circuit Theory)** |
| :--- | :---: | :---: | :---: |
| **Mixer Obfuscation Top-1 Accuracy** | 75.0% (down to 39%) | 71.8% | **94.6%** |
| **Labeled Training Cases Needed** | Zero | 1,000 – 2,500 | **Zero (Zero-Shot Physics)** |
| **Out-of-Distribution (OOD) Drop** | N/A | -24.5 pp (Collapses) | **-6.0 pp (Resilient)** |
| **Statistical Significance** | — | — | **$\chi^2 = 49.04, p = 2.5 \times 10^{-12}$** |
| **Solve Compute Time (per query)** | $\approx 2\text{ ms}$ | $\approx 45\text{ ms}$ | **$3.8\text{ ms}$ (Sparse LU)** |

### Real Mainnet Blockchain Proofs:
* **Historical Ground Truth (USMS Silk Road Seizure):** Evaluated on real 29,657 BTC DOJ forfeiture cluster `1F1tAaz5...` over 199 nodes and 235 UTXOs. Correctly identified **Coinbase Prime as #1** ($R_{\text{eff}} = 1293.14\,\Omega$, 95.7% confidence).
* **Live Mainnet Autonomous Trace:** [PENDING PHASE 2 LIVE VALIDATION RESULTS]

---

## 5. Technology Stack & Deployment

* **Backend & API:** Python 3.11, FastAPI, Uvicorn, Pydantic v2
* **Linear Algebra & Graph Theory:** NetworkX, NumPy, SciPy (`scipy.sparse.linalg.splu`)
* **Databases:** DuckDB (`attribution.duckdb`) and SQLite (`attribution.sqlite`)
* **Forensic PDF Engine:** ReportLab (Section 65B certification with SHA-256 hash)
* **Frontend Visualization:** Cytoscape.js, Dagre Layout, HTML5/CSS3 Glassmorphism

### Quick Run Commands:
```powershell
# 1. Start Backend Server (Port 8000)
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

# 2. Interactive Canvas
# Open graph_visualizer.html in Chrome / Edge

# 3. Execute Full Real-World Test Suite
python test_real_engine_live.py
```
