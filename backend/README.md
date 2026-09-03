# SIH26182 — Backend & Data Ingestion Pipeline (General CSE)

This entire module is completely self-contained within `backend/` to isolate Backend, Ingestion, Database, and API services from the core engine and other workstreams on the `main` branch.

---

## Architecture Overview

```
[ Blockstream / Mempool.space API ] ──► [ blockstream_client.py ] ──┐
(Live Bitcoin UTXO Data)                                            │
                                                                    │
[ Etherscan Developer API ]         ──► [ etherscan_client.py ]   ──┤
(Live Ethereum/EVM Account Data)                                    │
                                                                    ▼
[ GraphSense TagPacks & Crypto-Tags]──► [ tagpack_loader.py ]     ──► [ DuckDB / SQLite Storage ]
(YAML/JSON/CSV exchange tags)           (Sanitize & Normalize)        (entity_tags & transaction_edges)
                                                                    ▲
[ Elliptic++ Academic Dataset ]     ──► [ elliptic_loader.py ]    ──┤
(AML benchmark ground truth)                                        │
                                                                    │
[ Local Mock/Seed Data ]            ──► [ seed_demo.py ]          ──┘
(25 offline laundering scenarios)                                   │
                                                                    ▼
                                                      [ Subgraph Extractor ]
                                                      (extractor.py)
                                                      - k-hop BFS traversal (BTC + ETH)
                                                      - VASP boundary stopping
                                                      - NetworkX DiGraph + weights
                                                                    │
                                                                    ▼
                                                      [ Core Laplacian Solver ]
                                                      (src.attribution.engine.AttributionEngine Lx = b)
                                                                    │
                                                                    ▼
                                                      [ FastAPI Orchestrator ]
                                                      - POST /api/v1/investigate
                                                      - GET  /api/v1/graph/subgraph/{address}
                                                      - POST /api/v1/sahyog/dispatch
                                                      - GET  /api/v1/reports/{case_id}/export
                                                      - POST /attribute (frozen contract)
```

---

## Directory Structure

```
backend/
├── config.py                      # USE_LIVE_API toggle, DB paths, hop limits
├── data/                          # Embedded DuckDB storage & seed artifacts
├── database/
│   ├── db.py                      # DuckDB connection & schema/index initializer (with SQLite fallback)
│   └── repositories.py            # Fast indexed queries for tags & transactions
├── ingestion/
│   ├── schemas.py                 # Ingestion dataclasses & uniform Edge model
│   ├── tagpack_loader.py          # GraphSense TagPack parser (YAML/JSON/CSV + remote URLs)
│   ├── blockstream_client.py      # Blockstream + Mempool.space failover client
│   ├── etherscan_client.py        # Etherscan EVM account-based transaction fetcher
│   ├── elliptic_loader.py         # Academic Elliptic / Elliptic++ dataset parser
│   ├── extractor.py               # Multi-chain k-hop Subgraph Extractor
│   ├── seed_demo.py               # Fallback offline seeder (25 scenarios + Elliptic++)
│   ├── sample_data/               # Elliptic++ benchmark sample CSV
│   └── tagpacks/                  # Curated GraphSense VASP & mixer tags
│       ├── graphsense_exchanges.yaml
│       ├── exchanges.json
│       └── mixers.json
├── models/
│   ├── common.py                  # Crypto address regex (BTC Base58/Bech32, EVM, synth)
│   ├── attribution.py             # /investigate & /attribute Pydantic schemas
│   ├── graph.py                   # Cytoscape.js / D3.js node & edge models
│   ├── sahyog.py                  # Section 91 CrPC lawful dispatch schemas
│   └── reports.py                 # Report generation models
├── services/
│   ├── attribution_service.py     # Bridges Extractor -> AttributionEngine -> confidence scores
│   ├── graph_service.py           # Prepares Cytoscape graph with node classifications
│   ├── sahyog_service.py          # Lawful disclosure dispatch & ACK token tracking
│   └── report_service.py          # ReportLab forensic PDF report compiler (Section 65B)
├── routers/
│   ├── investigate.py             # POST /api/v1/investigate & POST /attribute
│   ├── graph.py                   # GET /api/v1/graph/subgraph/{address}
│   ├── sahyog.py                  # POST /api/v1/sahyog/dispatch
│   └── reports.py                 # GET /api/v1/reports/{case_id}/export
├── main.py                        # FastAPI app setup, CORS, and router mounting
├── requirements.txt               # Backend-specific dependencies
├── Dockerfile                     # Isolated container build
├── docker-compose.yml             # Isolated container stack
└── tests/                         # Full automated test suite
    ├── test_db.py
    ├── test_tagpack_loader.py
    ├── test_blockstream.py
    ├── test_extractor.py
    ├── test_investigate_api.py
    ├── test_sahyog_dispatch.py
    └── test_report_export.py
```

---

## Quick Start (Isolated in `backend/`)

### 1. Install Backend Dependencies
```bash
pip install -r backend/requirements.txt
```

### 2. Seed Offline Demo Dataset (Zero Network Latency for Judging)
```bash
python -m backend.ingestion.seed_demo
```

### 3. Run Backend Test Suite
```bash
pytest backend/tests/ -v
```

### 4. Start the Backend API
```bash
uvicorn backend.main:app --reload --port 8000
```
API Documentation will be available at: `http://localhost:8000/docs`.

---

## Endpoints Reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/investigate` | Triggers k-hop traversal, builds Laplacian, ranks VASPs by effective resistance, computes confidence |
| `GET` | `/api/v1/graph/subgraph/{address}` | Returns Cytoscape.js nodes and edges with role classifications (`suspect`, `mixer_hop`, `candidate_vasp`, `background`) |
| `POST` | `/api/v1/sahyog/dispatch` | Dispatches formal Section 91 CrPC lawful freeze / KYC notice, returning token `SAHYOG-ACK-2026-XXXX` |
| `GET` | `/api/v1/sahyog/{ack_token}` | Queries status and details of a previously submitted SAHYOG notice |
| `GET` | `/api/v1/reports/{case_id}/export` | Streams court-admissible forensic incident report PDF with Section 65B Indian Evidence Act certificate |
| `POST` | `/attribute` | Frozen legacy endpoint matching `docs/ENGINE_CONTRACT.md` |
| `GET` | `/health` | System health check and runtime flag status (`USE_LIVE_API`) |
