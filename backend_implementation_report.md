# SIH26182 — Backend Implementation, Architecture & Function Reference Report

> **Comprehensive Technical Specification of the SIH26182 Backend Engine**  
> *End-to-End Architectural Flow, Ingestion Pipelines, Grounded Graph Laplacian ($Lx = b$), Code Snippets, and Function Input/Output Contracts.*

---

## Table of Contents
1. [Executive Summary & Problem Statement](#1-executive-summary--problem-statement)
2. [How the Backend Works (Complete Architectural Flow)](#2-how-the-backend-works-complete-architectural-flow)
3. [Module & Function Technical Reference (With Code Snippets)](#3-module--function-technical-reference-with-code-snippets)
   - [A. Application Entrypoint & Config](#a-application-entrypoint--config)
   - [B. Database & Storage Layer](#b-database--storage-layer)
   - [C. Ingestion & Subgraph Extraction](#c-ingestion--subgraph-extraction)
   - [D. Validation & Pydantic Contracts](#d-validation--pydantic-contracts)
   - [E. Core Services Layer](#e-core-services-layer)
   - [F. API Routers](#f-api-routers)
4. [Master Function Input & Output Reference Table](#4-master-function-input--output-reference-table)
5. [How to Convert This Report to PDF](#5-how-to-convert-this-report-to-pdf)

---

## 1. Executive Summary & Problem Statement

### The Fundamental Flaw of Traditional Blockchain Forensics
Commercial forensics suites (Chainalysis, Elliptic, basic graph search) rely heavily on **Shortest-Path algorithms (Dijkstra / A\*)** or **Maximum-Flow heuristics**. In real-world financial laundering, adversaries exploit these heuristics using:

1. **The Mixer Entropy Trap (CoinJoin, Wasabi, Tornado.cash):**
   - Suspect funds enter high-entropy mixing pools with uniform denomination outputs.
   - Shortest-path algorithms treat all paths as equally cheap or get permanently trapped in the pool.
2. **Peeling Chains & Low-Fee Decoy Traps:**
   - A launderer splits $100\text{ BTC}$ into a $0.001\text{ BTC}$ decoy transfer (2 hops) and routes the remaining $99.999\text{ BTC}$ through a 5-hop peel chain to a cash-out exchange.
   - Shortest-path incorrectly attributes the funds to the decoy wallet.
3. **Combinatorial Search Explosion ($O(b^k)$):**
   - Unbounded BFS crawling addresses with high branching factors $b > 100$ (mining pools, exchange sweep clusters) produces $1,000,000+$ nodes by depth 3, crashing servers.

### The SIH26182 Circuit Theory Solution
Our engine transforms the transaction graph into an **Electrical Resistor Network**:
- **Nodes** = Wallet addresses.
- **Conductances ($w$)** = Transaction amounts (Satoshis / normalized ETH units).
- **Suspect Wallet** = Unit current source ($I = 1.0\text{ A}$).
- **Candidate VASPs (Exchanges)** = Dirichlet ground nodes ($V = 0\text{ V}$).
- **Attribution Confidence** = Inverse Effective Resistance ($\frac{1}{R_{\text{eff}}}$).

Instead of following a single path, our system computes the **Effective Resistance ($R_{\text{eff}}$)** between the suspect wallet and every candidate exchange by solving the **Grounded Graph Laplacian ($Lx = b$)**:

$$\mathbf{L}_{\text{grounded}} \cdot \mathbf{v} = \mathbf{I}_{\text{unit}}$$

Because current divides across parallel paths according to Kirchhoff's Laws, **Effective Resistance aggregates evidence across ALL parallel paths simultaneously**, making mixer splits and peeling chains mathematically transparent.

---

## 2. How the Backend Works (Complete Architectural Flow)

The following diagram and 7-step walkthrough illustrate the complete lifecycle of an investigation query:

```
[ Investigator / Web UI ]
           │
           │ HTTP POST /api/v1/investigate { suspect_address, depth_limit=4 }
           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. Request Validation & Lifespan Setup                                  │
│    • Pydantic checks address regex (BTC Base58/Bech32, EVM 0x...)       │
│    • Database initialization (DuckDB with SQLite fallback)              │
│    • Auto-seeds 25 demo laundering cases if database is empty           │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. Bounded Downstream Subgraph Extractor (backend/ingestion/extractor) │
│    • Directional Temporal Filter: Prunes edges where t_out < t_in - 2h  │
│    • High-Degree Super-Hub Pruning: Halts deeper expansion if deg >= 45 │
│    • Adaptive Volume Beam Search: Gathers top branches until >= 85%     │
│      cumulative volume mass is retained (bounded 3 to 12 branches)      │
│    • Halts traversal at known VASP boundaries (Dirichlet grounds)       │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. Multi-Tier Live Blockchain Ingestion                                 │
│    • Live Bitcoin: Mempool.space ──► Blockstream ──► Blockchain.info    │
│    • Proportional UTXO Haircut: Allocates vout by input satoshi stake   │
│    • Live Ethereum: Etherscan API normalized to satoshi-equivalent scale│
│    • Ingested edges cached in DuckDB/SQLite to eliminate repeat queries │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. Grounded Laplacian Circuit Solver (src/attribution/engine.py)       │
│    • Ground Node 0 (V_0 = 0V) to eliminate Laplacian null space         │
│    • Factorize grounded Laplacian via SciPy Sparse LU: L_grounded = splu│
│    • Inject unit current vector b: (+1.0A at suspect, -1.0A at VASP)    │
│    • Solve L * x = b  ==>  R_eff = |v_suspect - v_candidate|            │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. Inverse-Resistance Confidence Normalization                          │
│    • Conductance weights: weight_i = 1.0 / (R_eff,i + 1e-6)             │
│    • Normalized probability: confidence_i = weight_i / sum(weights)     │
│    • Lower resistance yields mathematically higher attribution rank     │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 6. Case Persistence & SAHYOG Statutory Dispatch                         │
│    • Logs case in investigation_cases table with unique case_id         │
│    • Issues formal Section 91 CrPC freeze directive to destination VASP │
│    • Computes SHA-256 audit hash and issues SAHYOG-ACK-2026-XXXXXX token│
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 7. Court-Admissible Reporting & Visualization                           │
│    • Returns Cytoscape.js subgraphs (GET /api/v1/graph/subgraph/{addr}) │
│    • Compiles Section 65B Indian Evidence Act certified PDF dossier     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Module & Function Technical Reference (With Code Snippets)

---

### A. Application Entrypoint & Config

#### File: `backend/config.py`
Defines filesystem paths, database locations, runtime flags, API parameters, and CORS origins.

##### Code Snippet:
```python
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "attribution.duckdb"
SQLITE_DB_PATH = DATA_DIR / "attribution.sqlite"

USE_LIVE_API = os.getenv("USE_LIVE_API", "true").lower() in ("true", "1", "yes")
BLOCKSTREAM_BASE_URL = os.getenv("BLOCKSTREAM_BASE_URL", "https://mempool.space/api")
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "12"))
API_REQUEST_DELAY_MS = int(os.getenv("API_REQUEST_DELAY_MS", "80"))

DEFAULT_HOP_DEPTH = int(os.getenv("DEFAULT_HOP_DEPTH", "3"))
MAX_HOP_DEPTH = int(os.getenv("MAX_HOP_DEPTH", "10"))
MAX_SUBGRAPH_NODES = int(os.getenv("MAX_SUBGRAPH_NODES", "3500"))
```

---

#### File: `backend/main.py`
Instantiates FastAPI, manages lifecycle hooks, applies CORS middleware, and mounts routers.

##### 1. `lifespan(app: FastAPI)`
* **Description**: Async context manager for application startup and shutdown. Connects to database, initializes tables via `init_db(db)`, and seeds 25 demo cases if empty.
* **Inputs**: `app: FastAPI`
* **Outputs**: Async generator yielding control.
* **Code Snippet**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing SIH26182 Backend Engine...")
    db = get_db_connection()
    init_db(db)

    tag_repo = EntityTagRepository(db)
    if not tag_repo.list_all_vasp_addresses():
        logger.info("Empty database detected. Seeding offline demo dataset...")
        seed_database(num_cases=25)

    logger.info(f"SIH26182 Engine Ready (USE_LIVE_API={USE_LIVE_API}).")
    yield
    logger.info("Shutting down backend services.")
```

##### 2. `health_check()`
* **Route**: `GET /health`
* **Description**: Simple health probe endpoint.
* **Inputs**: None
* **Outputs**: `dict`: `{"status": "healthy", "service": "...", "version": "1.0.0", "use_live_api": bool}`

---

### B. Database & Storage Layer

#### File: `backend/database/db.py`
Thread-safe database connection manager supporting DuckDB with automatic SQLite fallback.

##### Class: `DatabaseConnection`
* **`connect(self)`**:
  * **Description**: Returns open DuckDB connection. If DuckDB is unavailable or throws an error, falls back to SQLite with `check_same_thread=False` and `sqlite3.Row` row factory.
  * **Inputs**: None
  * **Outputs**: Connection instance (`duckdb.DuckDBPyConnection` or `sqlite3.Connection`).
  * **Code Snippet**:
```python
def connect(self):
    with self._lock:
        if self._conn is not None:
            return self._conn
        if self.use_duckdb:
            try:
                import duckdb
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                self._conn = duckdb.connect(database=str(self.db_path), read_only=False)
                return self._conn
            except Exception as e:
                logger.error(f"DuckDB connection failed: {e}. Falling back to SQLite.")
                self.use_duckdb = False
        SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(SQLITE_DB_PATH), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        return self._conn
```

* **`execute(self, query: str, parameters: tuple = ())`**: Executes parameterized query under thread lock. Returns cursor.
* **`fetchall(self, query: str, parameters: tuple = ()) -> list`**: Returns all matching rows.
* **`fetchone(self, query: str, parameters: tuple = ()) -> Any`**: Returns single matching row or `None`.

##### `init_db(db: DatabaseConnection | None = None) -> None`
* **Description**: Creates 5 core tables and their performance indices:
  1. `entity_tags`: Tagged addresses, entity names, categories (`exchange`, `mixer`, `illicit`).
  2. `transaction_edges`: Directed edges (`tx_hash`, `source`, `target`, `amount_satoshis`, `timestamp`, `chain`).
  3. `sahyog_dispatches`: Section 91 CrPC notice dispatch records.
  4. `investigation_cases`: Audit results, suspect address, top VASP, confidence score, and JSON payload.
  5. `crawled_addresses`: Registry of addresses crawled from live APIs to prevent re-fetching.
* **Inputs**: `db: Optional[DatabaseConnection]`
* **Outputs**: `None`

---

#### File: `backend/database/repositories.py`
Data Access Objects (DAOs) encapsulating SQL execution.

##### 1. `EntityTagRepository.get_vasp_candidates_for_addresses(self, addresses: List[str]) -> List[Dict[str, Any]]`
* **Description**: Filters input address list to return those categorized as `exchange`, `custodial`, or `vasp`.
* **Inputs**: `addresses: List[str]`
* **Outputs**: `List[dict]` containing `address`, `entity_name`, `category`, `confidence`.
* **Code Snippet**:
```python
def get_vasp_candidates_for_addresses(self, addresses: List[str]) -> List[Dict[str, Any]]:
    if not addresses:
        return []
    placeholders = ",".join(["?"] * len(addresses))
    query = f"""
        SELECT address, entity_name, category, confidence 
        FROM entity_tags 
        WHERE address IN ({placeholders}) AND category IN ('exchange', 'custodial', 'vasp')
    """
    rows = self.db.fetchall(query, tuple(addresses))
    return [{"address": r[0], "entity_name": r[1], "category": r[2], "confidence": r[3]} for r in rows]
```

##### 2. `TransactionEdgeRepository.get_connected_edges(self, address: str, limit: int = 100) -> List[Dict[str, Any]]`
* **Description**: Returns all incoming and outgoing edges for an address, ordered by volume descending.
* **Inputs**: `address: str`, `limit: int` (default 100).
* **Outputs**: `List[Dict[str, Any]]` (`tx_hash`, `source_address`, `target_address`, `amount_satoshis`, `timestamp`).

##### 3. `CaseRepository.save_case(self, case_id: str, suspect_address: str, top_vasp: str, confidence: float, results_data: dict) -> None`
* **Description**: Saves or updates investigation results with serialized JSON.
* **Inputs**: `case_id: str`, `suspect_address: str`, `top_vasp: str`, `confidence: float`, `results_data: dict`
* **Outputs**: `None`

---

### C. Ingestion & Subgraph Extraction

#### File: `backend/ingestion/schemas.py`
Immutable dataclasses standardizing data structures.

##### Code Snippet:
```python
@dataclass(frozen=True)
class UniformEdge:
    source_address: str
    target_address: str
    amount_satoshis: int
    tx_hash: str
    timestamp: Optional[datetime] = None
    chain: str = "BTC"
    is_coinbase: bool = False

    @property
    def amount_btc(self) -> float:
        return self.amount_satoshis / 100_000_000.0

@dataclass(frozen=True)
class EntityTagItem:
    address: str
    entity_name: str
    category: str
    chain: str = "BTC"
    source: str = "GraphSense"
    confidence: float = 1.0
```

---

#### File: `backend/ingestion/blockstream_client.py`
3-tier live Bitcoin fetcher (Mempool.space $\rightarrow$ Blockstream $\rightarrow$ Blockchain.info).

##### `resolve_utxo_edges(self, tx_obj: dict) -> List[UniformEdge]`
* **Description**: Deconstructs raw Bitcoin transactions into directed edges using **Proportional UTXO Haircut Allocation**. Each source input is apportioned outgoing output satoshis proportionally according to its fraction of total inputs.
* **Inputs**: `tx_obj: dict` (Raw transaction JSON).
* **Outputs**: `List[UniformEdge]`.
* **Code Snippet**:
```python
def resolve_utxo_edges(self, tx_obj: dict) -> List[UniformEdge]:
    tx_hash = tx_obj.get("txid", "")
    inputs = tx_obj.get("vin", [])[:15]
    outputs = tx_obj.get("vout", [])[:15]

    source_values = {}
    for vin in inputs:
        prevout = vin.get("prevout")
        if prevout and "scriptpubkey_address" in prevout:
            addr = prevout["scriptpubkey_address"]
            val = prevout.get("value", 0)
            if addr:
                source_values[addr] = source_values.get(addr, 0) + val

    sources = list(source_values.keys())
    total_input_value = sum(source_values.values())
    edges = []

    for vout in outputs:
        target_addr = vout.get("scriptpubkey_address")
        value = vout.get("value", 0)
        if not target_addr or value <= 0:
            continue
        for src in sources:
            if src != target_addr:
                # Proportional Haircut allocation
                if total_input_value > 0 and source_values[src] > 0:
                    allocated_amount = max(1, round(value * (source_values[src] / total_input_value)))
                else:
                    allocated_amount = max(1, value // len(sources))
                edges.append(UniformEdge(src, target_addr, allocated_amount, tx_hash, timestamp=None))
    return edges
```

##### `get_or_fetch_edges(self, address: str) -> List[UniformEdge]`
* **Description**: Checks if address is already crawled in local DB. If not, queries live APIs with failover, resolves edges, saves to database, marks address crawled, and returns edges.
* **Inputs**: `address: str`
* **Outputs**: `List[UniformEdge]`

---

#### File: `backend/ingestion/extractor.py`
Downstream Subgraph Extractor implementing bounded traversal with heuristic pruning.

##### `extract_subgraph(self, suspect_address: str, max_depth: int = 3, chain: str = "BTC") -> Tuple[nx.Graph, List[str], Dict[str, dict]]`
* **Description**: Traverses downstream transaction paths starting at `suspect_address`:
  - **Temporal Directional Filter**: Prunes edges where $t_{\text{out}} < t_{\text{in}} - 2\text{h}$ to prevent backward-in-time traversal.
  - **High-Degree Super-Hub Pruning**: If a non-suspect node has $\ge 45$ edges (mining pools, mixers), halts deeper branch traversal.
  - **Adaptive Cumulative Volume Beam Search**: Accumulates candidate branches until $\ge 85\%$ of candidate volume mass is retained (bounded 3 to 12 branches).
  - **VASP Boundary Halting**: Stops when reaching known exchange addresses.
* **Inputs**: `suspect_address: str`, `max_depth: int`, `chain: str`
* **Outputs**: `Tuple[nx.Graph, List[str], Dict[str, dict]]`:
  - `G (nx.Graph)`: Weighted NetworkX graph.
  - `candidate_vasps`: List of discovered exchange wallet addresses.
  - `node_metadata`: Map of address to role, entity name, and category.
* **Code Snippet**:
```python
# 1. Directional Temporal Causality Filter
if t_arrival is not None and edge.timestamp is not None and edge.source_address == curr_addr:
    if edge.timestamp < t_arrival - timedelta(hours=2):
        continue  # Funds cannot exit before they arrive

# 2. Super Hub Detection
if len(edges) >= 45 and curr_addr != suspect_address:
    node_metadata[curr_addr]["role"] = "suspected_hub"
    logger.info(f"Node {curr_addr} is a high-degree hub. Halting deeper branch expansion.")
    continue

# 3. Adaptive Volume Beam Search
total_candidate_vol = sum(e.amount_satoshis for e, _ in candidate_hops)
accumulated_vol = 0
hops_queued = 0
for edge, next_hop in candidate_hops:
    visited_nodes.add(next_hop)
    queue.append((next_hop, depth + 1, edge.timestamp))
    hops_queued += 1
    accumulated_vol += edge.amount_satoshis
    if hops_queued >= 3:
        if hops_queued >= 12 or (total_candidate_vol > 0 and (accumulated_vol / total_candidate_vol) >= 0.85):
            break
```

---

### D. Validation & Pydantic Contracts

#### File: `backend/models/common.py`
##### `validate_crypto_address(val: str) -> str`
* **Description**: Validates that an address matches Bitcoin Base58 regex (`^[13]...`), Bitcoin Bech32 regex (`^bc1...`), EVM regex (`^0x[a-fA-F0-9]{40}$`), or synthetic test identifiers (`suspect_*`, `VASP_*`, `mixer_*`, `peel_*`).
* **Inputs**: `val: str`
* **Outputs**: `str` (trimmed address) or raises `ValueError`.

##### Code Snippet:
```python
BTC_BASE58_REGEX = re.compile(r"^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$")
BTC_BECH32_REGEX = re.compile(r"^bc1[a-z0-9]{39,59}$")
EVM_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")
SYNTHETIC_REGEX = re.compile(r"^(suspect|VASP|mixer|hop|bg|demo|decoy|peel|tx)_[a-zA-Z0-9_-]+$")

def validate_crypto_address(val: str) -> str:
    trimmed = str(val).strip()
    if (
        BTC_BASE58_REGEX.match(trimmed)
        or BTC_BECH32_REGEX.match(trimmed)
        or EVM_REGEX.match(trimmed)
        or SYNTHETIC_REGEX.match(trimmed)
    ):
        return trimmed
    raise ValueError(f"Invalid cryptocurrency address: '{trimmed}'.")

CryptoAddress = Annotated[str, BeforeValidator(validate_crypto_address)]
```

---

#### File: `backend/models/attribution.py`
* **`InvestigateRequest`**: `suspect_address: CryptoAddress`, `chain: str = "BTC"`, `depth_limit: int = 4`, `candidate_vasps: Optional[List[str]]`.
* **`RankedVaspItem`**: `vasp_name: str`, `candidate_address: str`, `effective_resistance: float`, `confidence_score: float`.
* **`GraphSummary`**: `nodes_analyzed: int`, `edges_analyzed: int`, `compute_time_ms: float`, `solver_method: str = "effective_resistance"`.
* **`InvestigateResponse`**: `case_id: str`, `suspect_address: str`, `ranked_vasps: List[RankedVaspItem]`, `graph_summary: GraphSummary`.

---

### E. Core Services Layer

#### File: `backend/services/attribution_service.py`
Connects extraction, candidate selection, the Grounded Laplacian Solver, and confidence normalization.

##### `investigate(self, req: InvestigateRequest) -> InvestigateResponse`
* **Description**:
  1. Extracts the $k$-hop neighborhood graph around the suspect wallet.
  2. Resolves candidate VASPs (from explicit request $\rightarrow$ discovered graph tags $\rightarrow$ all known VASPs in graph).
  3. Instantiates `AttributionEngine(graph)` and executes the Grounded Laplacian Solver ($Lx = b$).
  4. Converts effective resistance ($R_{\text{eff}}$) into probabilistic confidence scores via inverse conductance:
     $$w_i = \frac{1}{R_{\text{eff}, i} + 10^{-6}}, \quad \text{confidence}_i = \frac{w_i}{\sum w}$$
  5. Saves the case to the `investigation_cases` table.
  6. Returns `InvestigateResponse`.
* **Inputs**: `req: InvestigateRequest`
* **Outputs**: `InvestigateResponse`
* **Code Snippet**:
```python
def investigate(self, req: InvestigateRequest) -> InvestigateResponse:
    t0 = time.perf_counter()
    graph, discovered_vasps, metadata = self.extractor.extract_subgraph(
        suspect_address=req.suspect_address, max_depth=req.depth_limit, chain=req.chain
    )
    if graph.number_of_nodes() <= 1:
        raise ValueError(f"Suspect wallet '{req.suspect_address}' has no transaction history")

    candidate_pool = req.candidate_vasps or discovered_vasps or self.tag_repo.list_all_vasp_addresses()
    candidates_in_graph = [c for c in candidate_pool if c in graph.nodes and c != req.suspect_address]

    # Core Laplacian Solver (AttributionEngine: Lx = b)
    engine = AttributionEngine(graph, weight_attr="weight")
    attr_result = engine.attribute(req.suspect_address, candidates_in_graph)

    # Inverse Resistance Normalization into Probabilities
    inverse_weights = {
        c: 1.0 / (attr_result.scores[c] + 1e-6)
        for c in attr_result.ranked_candidates if not math.isinf(attr_result.scores[c])
    }
    total_weight = sum(inverse_weights.values()) or 1.0

    ranked_items = [
        RankedVaspItem(
            vasp_name=metadata.get(c, {}).get("entity", c),
            candidate_address=c,
            effective_resistance=round(attr_result.scores[c], 4),
            confidence_score=round(inverse_weights.get(c, 0.0) / total_weight, 3),
        )
        for c in attr_result.ranked_candidates
    ]

    case_id = f"CASE-{req.suspect_address[:8].upper()}-{int(time.time())}"
    response = InvestigateResponse(
        case_id=case_id, suspect_address=req.suspect_address,
        ranked_vasps=ranked_items,
        graph_summary=GraphSummary(
            nodes_analyzed=graph.number_of_nodes(),
            edges_analyzed=graph.number_of_edges(),
            compute_time_ms=round((time.perf_counter() - t0) * 1000, 2),
            solver_method=attr_result.method
        )
    )
    self.case_repo.save_case(case_id, req.suspect_address, ranked_items[0].vasp_name, ranked_items[0].confidence_score, response.model_dump())
    return response
```

---

#### File: `backend/services/sahyog_service.py`
Simulates statutory notices under Section 91 CrPC.

##### `dispatch_notice(self, req: SahyogDispatchRequest) -> SahyogDispatchResponse`
* **Description**: Creates official tracking token (`SAHYOG-ACK-2026-XXXXXX`), calculates SHA-256 audit hash across parameters, persists record in `sahyog_dispatches`, and returns response with mock compliance URL.
* **Inputs**: `req: SahyogDispatchRequest`
* **Outputs**: `SahyogDispatchResponse`
* **Code Snippet**:
```python
def dispatch_notice(self, req: SahyogDispatchRequest) -> SahyogDispatchResponse:
    ack_token = f"SAHYOG-ACK-2026-{uuid.uuid4().hex[:6].upper()}"
    now_str = datetime.utcnow().isoformat() + "Z"

    payload_raw = f"{req.case_id}:{req.suspect_address}:{req.target_vasp}:{req.action}:{now_str}"
    dispatch_hash = hashlib.sha256(payload_raw.encode("utf-8")).hexdigest()

    self.repo.create_dispatch(
        ack_token=ack_token, case_id=req.case_id, suspect_address=req.suspect_address,
        target_vasp=req.target_vasp, action=req.action, officer_name=req.officer_name,
        jurisdiction=req.jurisdiction, law_section=req.law_section,
        dispatch_hash=dispatch_hash, status="SUBMITTED"
    )
    compliance_url = f"https://compliance.{req.target_vasp.lower().replace(' ', '')}.in/le-portal/v2/dispatches/{ack_token}"
    return SahyogDispatchResponse(
        ack_token=ack_token, case_id=req.case_id, suspect_address=req.suspect_address,
        target_vasp=req.target_vasp, action=req.action, status="SUBMITTED",
        timestamp=now_str, dispatch_hash=dispatch_hash, vasp_compliance_portal=compliance_url
    )
```

---

#### File: `backend/services/report_service.py`
Generates court-admissible forensic incident dossiers.

##### `generate_pdf_report(self, case_id: str) -> io.BytesIO`
* **Description**: Builds a ReportLab document containing Executive Summary, Attribution Matrix, Graph Computation Metrics, and Section 65B Indian Evidence Act Certificate (with SHA-256 integrity hash).
* **Inputs**: `case_id: str`
* **Outputs**: `io.BytesIO` positioned at byte 0 ready for streaming.
* **Code Snippet**:
```python
def generate_pdf_report(self, case_id: str) -> io.BytesIO:
    case_data = self.case_repo.get_case(case_id) or self.case_repo.get_latest_case_by_suspect(case_id)
    if not case_data:
        raise ValueError(f"Case ID or Suspect '{case_id}' not found in database.")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    # Title & Meta Box
    # 1. Executive Forensic Summary
    # 2. Candidate VASP Attribution Matrix
    # 3. Section 65B Certificate:
    raw_hash = hashlib.sha256(f"{case_id}:{case_data['suspect_address']}:{case_data['top_vasp']}".encode()).hexdigest()
    cert_text = (
        f"It is certified that the cryptocurrency graph extraction and attribution outputs contained "
        f"in this dossier were produced by an automated digital forensics computer system during its lawful, "
        f"ordinary operation. Cryptographic integrity hash: SHA-256: {raw_hash}"
    )
    story.append(Paragraph(cert_text, body_style))
    doc.build(story)
    buffer.seek(0)
    return buffer
```

---

### F. API Routers

#### File: `backend/routers/investigate.py`
##### `investigate_wallet(req: InvestigateRequest) -> InvestigateResponse`
* **Route**: `POST /api/v1/investigate`
* **Inputs**: `req: InvestigateRequest` (JSON)
* **Outputs**: `InvestigateResponse` (JSON)
* **Code Snippet**:
```python
@router.post("/api/v1/investigate", response_model=InvestigateResponse)
def investigate_wallet(req: InvestigateRequest):
    try:
        return _service.investigate(req)
    except ValueError as e:
        err_msg = str(e)
        if "not found in" in err_msg or "no transaction history" in err_msg:
            raise HTTPException(status_code=404, detail=err_msg)
        raise HTTPException(status_code=400, detail=err_msg)
    except Exception as e:
        logger.exception("Unexpected error during investigation")
        raise HTTPException(status_code=500, detail=f"Internal attribution solver error: {str(e)}")
```

---

#### File: `backend/routers/graph.py`
##### `get_address_subgraph(address: str, depth: int = Query(3), chain: str = Query("BTC")) -> SubgraphResponse`
* **Route**: `GET /api/v1/graph/subgraph/{address}`
* **Inputs**: `address: str` (path), `depth: int` (query), `chain: str` (query)
* **Outputs**: `SubgraphResponse` (JSON containing Cytoscape nodes and edges)

---

#### File: `backend/routers/sahyog.py`
##### `dispatch_lawful_notice(req: SahyogDispatchRequest) -> SahyogDispatchResponse`
* **Route**: `POST /api/v1/sahyog/dispatch`
* **Inputs**: `req: SahyogDispatchRequest` (JSON)
* **Outputs**: `SahyogDispatchResponse` (JSON)

##### `get_dispatch_details(ack_token: str)`
* **Route**: `GET /api/v1/sahyog/{ack_token}`
* **Inputs**: `ack_token: str` (path)
* **Outputs**: `dict` of stored notice details

---

#### File: `backend/routers/reports.py`
##### `export_case_report(case_id: str) -> StreamingResponse`
* **Route**: `GET /api/v1/reports/{case_id}/export`
* **Inputs**: `case_id: str` (path)
* **Outputs**: `StreamingResponse` (media type `application/pdf`)

##### `export_backend_implementation_report() -> StreamingResponse`
* **Route**: `GET /api/v1/reports/backend-implementation/export`
* **Inputs**: None
* **Outputs**: `StreamingResponse` (media type `application/pdf`, filename `SIH26182_Backend_Implementation_Report.pdf`)

---

## 4. Master Function Input & Output Reference Table

| Component / Function | HTTP Route / Class Method | Inputs (Parameters & Types) | Outputs (Return Value & Types) |
| :--- | :--- | :--- | :--- |
| **Investigate Wallet** | `POST /api/v1/investigate` | `req: InvestigateRequest` (`suspect_address`, `chain`, `depth_limit`, `candidate_vasps`) | `InvestigateResponse` (`case_id`, `suspect_address`, `ranked_vasps`, `graph_summary`) |
| **Legacy Attribution** | `POST /attribute` | `req: AttributionRequest` (`suspect_wallet`, `candidate_vasps`) | `AttributionResponse` (`suspect`, `ranked_candidates`, `scores`, `method`) |
| **Cytoscape Subgraph** | `GET /api/v1/graph/subgraph/{address}` | `address: str`, `depth: int = 3`, `chain: str = "BTC"` | `SubgraphResponse` (`suspect_address`, `nodes`, `edges`, `stats`) |
| **SAHYOG Notice** | `POST /api/v1/sahyog/dispatch` | `req: SahyogDispatchRequest` (`case_id`, `suspect_address`, `target_vasp`, `action`, `officer`, etc.) | `SahyogDispatchResponse` (`ack_token`, `dispatch_hash`, `compliance_portal`, `status`) |
| **SAHYOG Status** | `GET /api/v1/sahyog/{ack_token}` | `ack_token: str` (path) | `dict` (Stored statutory notice details) |
| **Export Case PDF** | `GET /api/v1/reports/{case_id}/export` | `case_id: str` (path) | `StreamingResponse` (PDF document) |
| **Export Backend PDF**| `GET /api/v1/reports/backend-implementation/export`| None | `StreamingResponse` (Backend Implementation PDF) |
| **Health Check** | `GET /health` | None | `{"status": "healthy", "service": "...", "use_live_api": bool}` |
| **AttributionService.investigate** | Method | `req: InvestigateRequest` | `InvestigateResponse` |
| **GraphService.get_cytoscape_subgraph** | Method | `suspect_address: str`, `max_depth: int`, `chain: str` | `SubgraphResponse` |
| **SahyogService.dispatch_notice** | Method | `req: SahyogDispatchRequest` | `SahyogDispatchResponse` |
| **ReportService.generate_pdf_report** | Method | `case_id: str` | `io.BytesIO` (ReportLab PDF stream) |
| **SubgraphExtractor.extract_subgraph** | Method | `suspect_address: str`, `max_depth: int`, `chain: str` | `Tuple[nx.Graph, List[str], Dict[str, dict]]` |
| **BlockstreamClient.get_or_fetch_edges**| Method | `address: str` | `List[UniformEdge]` |
| **BlockstreamClient.resolve_utxo_edges**| Method | `tx_obj: dict` | `List[UniformEdge]` |
| **EtherscanClient.get_or_fetch_edges** | Method | `address: str` | `List[UniformEdge]` |
| **EtherscanClient.resolve_evm_edges** | Method | `raw_txs: List[dict]` | `List[UniformEdge]` |
| **TagPackLoader.load_from_text** | Method | `content: str`, `filename: str` | `int` (Count of valid tags inserted) |
| **TagPackLoader.sanitize_and_validate** | Method | `record: dict` | `Optional[tuple]` (Sanitized record) |
| **EllipticLoader.ingest_classes** | Method | `classes_csv_path: Path` | `int` (Count of labels ingested) |
| **EllipticLoader.ingest_edgelist** | Method | `edgelist_csv_path: Path`, `default_weight: int` | `int` (Count of edges ingested) |
| **DatabaseConnection.execute** | Method | `query: str`, `parameters: tuple` | Database Cursor |
| **DatabaseConnection.fetchall** | Method | `query: str`, `parameters: tuple` | `list` of row records |
| **DatabaseConnection.fetchone** | Method | `query: str`, `parameters: tuple` | Single row or `None` |
| **validate_crypto_address** | Standalone function | `val: str` | `str` (Validated address) or raises `ValueError` |

---

## 5. How to Convert This Report to PDF

You can convert this markdown document into a PDF through any of the following methods:

### Method 1: Interactive 1-Click Print (Immediate Vector PDF)
Open the companion HTML document in Chrome or Edge:  
👉 **[`Backend_Implementation_Report.html`](file:///d:/hackathon/SIH/sih26182/Backend_Implementation_Report.html)**  
- Click the floating **"Save / Print as PDF"** button (or press `Ctrl + P`).
- Destination: **Save as PDF** $\rightarrow$ Click **Save**.
- Generates an A4 vector PDF with page-break protection for code snippets and tables.

### Method 2: Python Script (ReportLab)
Execute the CLI compilation script in your terminal:
```powershell
python generate_backend_pdf.py
```
This compiles and writes `SIH26182_Backend_Implementation_Report.pdf` directly into the project root.

### Method 3: VS Code / IDE Markdown PDF Extension
If you have the **Markdown PDF** or **Markdown Preview Enhanced** extension installed in VS Code:
1. Open this file: `Backend_Implementation_Report.md`.
2. Right-click anywhere in the editor.
3. Select **Markdown PDF: Export (pdf)**.
