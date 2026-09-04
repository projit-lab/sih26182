# Silk Road Dedicated Forensic Case & Attribution Engine

This directory contains a **completely standalone, self-contained backend and attribution engine** for the **Silk Road / US Marshals Service (USMS) Seizure & Liquidation Case**. It runs without modifying or altering the primary platform engine (`src/attribution/engine.py` and `backend/`).

---

## 1. Case Background & Ground Truth

* **Suspect Asset / Origin:** `1F1tAaz5x1HUXrCNLbtMDqcw6o5GNn4xqX`
  * **Description:** Seized by the FBI and US Marshals from the Silk Road infrastructure following the October 2013 takedown of Ross Ulbricht ("Dread Pirate Roberts").
  * **Volume:** 29,657.19 BTC seized, subsequently moved and auctioned.
* **Secondary Market Cluster:** `1DkyBEKt5S2GDtxBxgXd2LmUmMeFlxhAsj` (Silk Road Market Hot/Cold Wallets).
* **Individual X Seizure:** `1HQ3Go3ggs8pFnXuHVHRytPCq5fGG8Hbhx` (69,370 BTC seized by DOJ/IRS-CI in November 2020).
* **Ground Truth Cash-Out Destinations:**
  1. **Coinbase Prime Custody** (`3Cbq7aT1tY8kNxRdGQdurNo3DDPUk832d`) — Primary institutional liquidation and custody partner (highest volume conductance).
  2. **Kraken** (`3FZNfdHGmDsjBWP1NmJkP1mY41oK76n48A`) — Secondary exchange liquidation.
  3. **Binance** (`1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s`) — Minor/decoy diversion link.

---

## 2. Directory Structure

```
silkroad/
├── engine.py              # Dedicated Grounded Laplacian Solver (Lx = b)
├── backend.py             # Dedicated FastAPI server (endpoints: graph, investigate, report, sahyog)
├── loader.py              # Self-contained CLI test runner (executes in < 50ms)
├── entity_tags.json       # GraphSense & DOJ tags for Silk Road and destination VASPs
├── subgraph_edges.json    # Multi-hop transaction flow (peeling hops, mixers, and VASP deposits)
├── transactions.json      # Raw on-chain Bitcoin transactions fetched from Mempool.space
└── README.md              # Documentation
```

---

## 3. How to Run the Dedicated Engine (CLI)

To solve $Lx = b$, compute effective resistances, generate the Section 65B PDF report, and issue the SAHYOG notice directly:

```bash
python silkroad/loader.py
```

*Execution Time:* **< 50 milliseconds** (no external API calls or database overhead).

### Output Summary:
1. **Mathematical Solver:** Factorizes grounded $L$, solves $Lx = b$ for unit current between suspect and VASPs.
2. **Attribution Ranking:** **Coinbase Prime Custody** ranks **#1** ($R_{\text{eff}} \approx 0.08\,\Omega$, Confidence $\approx 78.4\%$).
3. **Evidence Dossier:** Generates `silkroad/SilkRoad_Forensic_Report.pdf` complying with Section 65B Indian Evidence Act.
4. **Lawful Dispatch:** Generates statutory Section 91 CrPC notice with SHA-256 cryptographic audit token.

---

## 4. How to Run the Dedicated Backend (FastAPI)

To run the dedicated Silk Road backend independently:

```bash
uvicorn silkroad.backend:app --port 8001
```

### Endpoints Available:
* `GET  /` — Service status & metadata
* `GET  /api/silkroad/graph` — Cytoscape-compatible node & edge graph
* `POST /api/silkroad/investigate` — Runs the $Lx = b$ attribution solver
* `GET  /api/silkroad/report` — Downloads Section 65B PDF report
