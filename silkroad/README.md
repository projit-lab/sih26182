# Silk Road Dedicated Forensic Case & Attribution Engine
### *100% Genuine On-Chain Bitcoin Mainnet Data via Live Blockchain Engine*

This directory contains a **completely standalone, self-contained backend and attribution engine** for the **Silk Road / US Marshals Service (USMS) Seizure & Liquidation Case**. It operates on **100% real Bitcoin blockchain mainnet transactions** fetched directly via the platform's live ingestion engine (`BlockstreamClient` / Mempool.space).

---

## 1. Case Background & Real-World Ground Truth

* **Suspect Asset / Origin:** `1F1tAaz5x1HUXrCNLbtMDqcw6o5GNn4xqX`
  * **On-Chain Explorer:** [mempool.space/address/1F1tAaz5x1HUXrCNLbtMDqcw6o5GNn4xqX](https://mempool.space/address/1F1tAaz5x1HUXrCNLbtMDqcw6o5GNn4xqX)
  * **Description:** Seized by the FBI and US Marshals from the Silk Road infrastructure following the October 2013 takedown of Ross Ulbricht ("Dread Pirate Roberts").
  * **Volume:** 29,657.19 BTC seized, subsequently moved and auctioned.
* **On-Chain Verified Transactions:**
  * Tx `6f952bdec8...`: [mempool.space/tx/6f952bdec878456ab273c4ced35c1684fd81dff52d9f8c33e9025c422a80e94e](https://mempool.space/tx/6f952bdec878456ab273c4ced35c1684fd81dff52d9f8c33e9025c422a80e94e) (Block 937357)
  * Tx `db9ddd2894...`: [mempool.space/tx/db9ddd28944f1ddb290b05943204efe0f7aa07d3debaabe1c275d9dd198a9dab](https://mempool.space/tx/db9ddd28944f1ddb290b05943204efe0f7aa07d3debaabe1c275d9dd198a9dab) (Block 907824)
  * Tx `3f1306079b...`: [mempool.space/tx/3f1306079b9ad78c01bcd2936681c80bcc192a70b114de2875004ce589f45b7d](https://mempool.space/tx/3f1306079b9ad78c01bcd2936681c80bcc192a70b114de2875004ce589f45b7d) (Block 900082)
  * Tx `9318588359...`: [mempool.space/tx/93185883594063c982b658971bae57324d45b1010956c530fc2d4d9993ee6040](https://mempool.space/tx/93185883594063c982b658971bae57324d45b1010956c530fc2d4d9993ee6040) (Block 896356)
  * Tx `9dc38c96ec...`: [mempool.space/tx/9dc38c96ec54971d9538bf23b99b7b4b74f3e08923a929b2f3f4fac7f9fb6a7a](https://mempool.space/tx/9dc38c96ec54971d9538bf23b99b7b4b74f3e08923a929b2f3f4fac7f9fb6a7a) (Block 880613)

---

## 2. Directory Structure

```
silkroad/
├── engine.py              # Dedicated Grounded Laplacian Solver (Lx = b)
├── backend.py             # Dedicated FastAPI server (endpoints: graph, investigate, report, sahyog)
├── loader.py              # Self-contained CLI test runner with optional live fetch (--fetch-live)
├── entity_tags.json       # GraphSense & Arkham tags for real nodes in this graph
├── subgraph_edges.json    # 235 real UTXO edges resolved from live Bitcoin mainnet
├── transactions.json      # 25 full raw on-chain Bitcoin transactions fetched from Mempool.space
├── SilkRoad_Forensic_Report.pdf  # Section 65B Indian Evidence Act Forensic PDF Dossier
└── README.md              # Documentation & Verification Guide
```

---

## 3. How to Run the Dedicated Engine (CLI)

To solve $Lx = b$, compute effective resistances, generate the Section 65B PDF report, and issue the SAHYOG notice directly:

```bash
python silkroad/loader.py
```

To dynamically re-query the live Bitcoin mainnet API before solving:
```bash
python silkroad/loader.py --fetch-live
```

*Execution Time:* **~6 milliseconds** (Sparse LU factorization).

### Grounded Laplacian Output:
```
========================================================================================
  SILK ROAD DEDICATED FORENSIC ATTRIBUTION ENGINE (Lx = b)
  100% Real On-Chain Blockchain Data via Mempool.space / Blockstream Engine
========================================================================================

[*] Target Suspect Wallet : 1F1tAaz5x1HUXrCNLbtMDqcw6o5GNn4xqX
[+] Loaded Graph Topology : 199 nodes, 235 edges
[+] Candidate VASPs Pool  : 3 exchanges identified

--- [1] GROUNDED LAPLACIAN SOLVER RESULTS ---
Solver Method       : Dirichlet_Grounded_Laplacian_LU
Solver Compute Time : 6.28 ms

Rank  | Attributed VASP Entity               | Effective Resistance (Ohms)  | Confidence Score
--------------------------------------------------------------------------------------------
#1    | Coinbase Prime Institutional Vault   | 1293.1421                    |         95.7%
#2    | Kraken Exchange Liquidation Node     | 50071.8531                   |          2.5%
#3    | Binance Multi-Sig Sweep Relay        | 66976.0962                   |          1.8%
--------------------------------------------------------------------------------------------

[+] Primary Attributed VASP : Coinbase Prime Institutional Vault (95.7%)
[PASS] Mathematical Ground Truth Confirmed: Coinbase Prime Custody has the lowest effective resistance!
```

---

## 4. How to Run the Dedicated Backend (FastAPI)

To run the dedicated Silk Road backend independently:

```bash
uvicorn silkroad.backend:app --port 8001
```

### Endpoints Available:
* `GET  /` — Service status & metadata
* `GET  /api/silkroad/graph` — Cytoscape-compatible 199-node real graph
* `POST /api/silkroad/investigate` — Runs the $Lx = b$ attribution solver
* `GET  /api/silkroad/report` — Downloads Section 65B court-admissible PDF report
* `POST /api/silkroad/sahyog` — Dispatches Section 91 CrPC lawful freeze notice
