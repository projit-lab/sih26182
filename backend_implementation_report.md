# SIH26182 Backend Implementation & Function Reference Report

This report provides an exhaustive, function-by-function technical audit of the `backend` directory in **SIH26182** (`Wallet-to-VASP Attribution & Ingestion Engine`). It details what has been implemented, how each subsystem functions, and specifies the exact inputs, parameters, and outputs for every function across all modules.

---

## 1. System Overview & Architecture

The `backend` folder provides the production orchestration and ingestion infrastructure connecting live blockchain networks (UTXO Bitcoin & EVM Ethereum) with the **Circuit Theory Graph Laplacian Attribution Engine ($Lx = b$)**, the **Cytoscape/D3 Graph Visualizer**, the **Indian Government SAHYOG Statutory Dispatcher (Section 91 CrPC)**, and **Section 65B Indian Evidence Act Forensic PDF Report Generation**.

```
                           +-----------------------------------------------+
                           |        Client / Frontend Visualizer           |
                           |   (graph_visualizer.html / Cytoscape.js)      |
                           +-----------------------+-----------------------+
                                                   | HTTP REST
                                                   v
                           +-----------------------------------------------+
                           |          FastAPI Application Layer            |
                           |              (backend/main.py)                |
                           +-----------------------+-----------------------+
                                                   |
         +--------------------+--------------------+--------------------+--------------------+
         |                    |                    |                    |                    |
         v                    v                    v                    v                    v
+-----------------+  +-----------------+  +-----------------+  +-----------------+  +-----------------+
| routers/        |  | routers/        |  | routers/        |  | routers/        |  | /health, /      |
| investigate.py  |  | graph.py        |  | sahyog.py       |  | reports.py      |  | System Status   |
+--------+--------+  +--------+--------+  +--------+--------+  +--------+--------+  +-----------------+
         |                    |                    |                    |
         v                    v                    v                    v
+-----------------+  +-----------------+  +-----------------+  +-----------------+
| services/       |  | services/       |  | services/       |  | services/       |
| attribution_... |  | graph_service.py|  | sahyog_service  |  | report_service  |
+--------+--------+  +--------+--------+  +--------+--------+  +--------+--------+
         |                    |                                         |
         |                    +--------------------+                    v
         |                                         |          +--------------------+
         v                                         v          | services/project_  |
+-----------------------------------------------------+       | report_generator   |
|         ingestion/extractor.py (SubgraphExtractor)  |       +--------------------+
|  - Temporal Causality Filter (t_out >= t_in - 2h)   |
|  - High-Degree Hub Pruning (degree >= 45)           |
|  - Adaptive Volume Beam Search (85% volume mass)    |
+--------------------------+--------------------------+
                           |
         +-----------------+-----------------+
         |                                   |
         v                                   v
+--------------------------+       +--------------------------+
| ingestion/               |       | ingestion/               |
| blockstream_client.py    |       | etherscan_client.py      |
| (Mempool -> Blockstream  |       | (Etherscan API           |
|  -> Blockchain.info)     |       |  normalized transfers)   |
+------------+-------------+       +------------+-------------+
             |                                  |
             +-----------------+----------------+
                               |
                               v
+-----------------------------------------------------+
|        Database Layer (DuckDB + SQLite Fallback)    |
|   - entity_tags (GraphSense / Crypto-Tags / VASP)   |
|   - transaction_edges (Uniform UTXO & EVM edges)    |
|   - sahyog_dispatches (Statutory notice registry)   |
|   - investigation_cases (Audit records)             |
|   - crawled_addresses (Cache tracking)              |
+-----------------------------------------------------+
```

---

## 2. Directory Structure

```
backend/
├── __init__.py                  # Package version declaration ("1.0.0")
├── api/
│   ├── __init__.py              # Package init
│   └── main.py                  # API entrypoint exposing app
├── config.py                    # Environment variables, timeouts, DB paths, CORS settings
├── main.py                      # FastAPI app initialization, lifespan, CORS, router mounting
├── database/
│   ├── __init__.py              # Re-exports get_db_connection, init_db
│   ├── db.py                    # Unified DuckDB / SQLite connection manager & table init
│   └── repositories.py          # Data Access Objects (EntityTag, TransactionEdge, Sahyog, Case)
├── ingestion/
│   ├── __init__.py              # Lazy import exports for ingestion tools
│   ├── blockstream_client.py    # 3-Tier Bitcoin API client (Mempool.space -> Blockstream -> B.info)
│   ├── elliptic_loader.py       # Parser for Elliptic/Elliptic++ AML benchmark dataset
│   ├── etherscan_client.py      # Ethereum/EVM account-based transaction fetcher
│   ├── extractor.py             # SubgraphExtractor (temporal filtering, beam search, hub pruning)
│   ├── fetch_datasets.py        # CLI tool to trigger ingestion across all sources
│   ├── schemas.py               # Dataclasses: UniformEdge, EntityTagItem
│   ├── seed_demo.py             # Generates 25 test cases & offline synthetic laundering graphs
│   └── tagpack_loader.py        # GraphSense TagPack parser (JSON, YAML, CSV)
├── models/
│   ├── __init__.py              # Re-exports all Pydantic schemas
│   ├── attribution.py           # Investigation request/response, VASP items, GraphSummary
│   ├── common.py                # Regex-based cryptocurrency address validator & CryptoAddress type
│   ├── graph.py                 # Cytoscape.js node & edge schemas, SubgraphResponse
│   ├── reports.py               # Forensic report metadata & export response schemas
│   └── sahyog.py                # SAHYOG statutory notice request & response models
├── routers/
│   ├── __init__.py              # Re-exports router modules
│   ├── graph.py                 # GET /api/v1/graph/subgraph/{address}
│   ├── investigate.py           # POST /api/v1/investigate and POST /attribute
│   ├── reports.py               # GET /api/v1/reports/{case_id}/export & /project-overview/export
│   └── sahyog.py                # POST /api/v1/sahyog/dispatch & GET /api/v1/sahyog/{ack_token}
├── services/
│   ├── __init__.py              # Re-exports service classes
│   ├── attribution_service.py   # Subgraph extraction, candidate resolution, Laplacian solve, scores
│   ├── graph_service.py         # Formats NetworkX subgraphs into Cytoscape-compatible models
│   ├── project_report_generator.py # Generates 5+ page comprehensive PDF project architecture report
│   ├── report_service.py        # Generates Section 65B LEA forensic PDF incident reports
│   └── sahyog_service.py        # Handles statutory notice creation, hashing, and token dispatch
└── tests/                       # Unit & integration test suite (8 test modules)
```

---

## 3. Detailed File, Class & Function Specification

---

### A. Core & Configuration

#### File: `backend/config.py`
Defines operational constants, filesystem paths, database file locations, network timeouts, and CORS policies.

- **Variables Configured**:
  - `BACKEND_DIR`: Absolute path to backend folder.
  - `PROJECT_ROOT`: Absolute path to the repository root.
  - `DATA_DIR`: Directory where databases reside (`backend/data`).
  - `DB_PATH`: Path to DuckDB database (`backend/data/attribution.duckdb`).
  - `SQLITE_DB_PATH`: Fallback path (`backend/data/attribution.sqlite`).
  - `USE_LIVE_API`: Boolean flag loaded from environment (`true`/`false`).
  - `BLOCKSTREAM_BASE_URL`: Base URL for Mempool/Blockstream API (`https://mempool.space/api`).
  - `REQUEST_TIMEOUT_SECONDS`: Maximum request wait duration (default: `12`).
  - `MAX_RETRIES`: Number of retry attempts on network error (default: `2`).
  - `API_REQUEST_DELAY_MS`: Delay between outgoing requests to prevent IP ban (default: `80` ms).
  - `DEFAULT_HOP_DEPTH`, `MAX_HOP_DEPTH`, `MAX_SUBGRAPH_NODES`: Traversal bounds (`3`, `10`, `3500`).
  - `CORS_ORIGINS`: Allowed origins (`localhost:3000`, `localhost:5173`, `*`).

---

#### File: `backend/main.py`
Initializes the FastAPI application, registers global lifecycle handlers, mounts CORS middleware, and exposes router endpoints.

##### `lifespan(app: FastAPI)`
* **Description**: Async context manager for application startup and shutdown. On startup, connects to the database, creates required tables (`init_db`), and checks whether VASP tags exist. If empty, automatically seeds 25 offline demo cases and TagPacks via `seed_database(num_cases=25)`.
* **Input**: `app: FastAPI` (Application instance).
* **Output**: Asynchronous generator yielding control to the running application.

##### `health_check()`
* **Description**: Health check endpoint (GET `/health`).
* **Input**: None.
* **Output**: `dict`:
  ```json
  {
    "status": "healthy",
    "service": "SIH26182 Backend & Ingestion Layer",
    "version": "1.0.0",
    "use_live_api": true
  }
  ```

##### `root()`
* **Description**: Root welcome endpoint (GET `/`).
* **Input**: None.
* **Output**: `dict` containing welcome message, documentation link (`/docs`), and health check link (`/health`).

---

### B. Database Subsystem

#### File: `backend/database/db.py`
Provides thread-safe relational database management for DuckDB with automatic SQLite fallback.

##### Class: `DatabaseConnection`
Thread-safe database connection wrapper utilizing an `RLock`.

* **`__init__(self, db_path: Path = DB_PATH, use_duckdb: bool = HAS_DUCKDB)`**
  * **Input**:
    * `db_path`: Target filesystem path for DuckDB file.
    * `use_duckdb`: Boolean indicating whether DuckDB is available.
  * **Output**: Instance of `DatabaseConnection`.

* **`connect(self) -> Connection`**
  * **Description**: Establishes or returns the existing open connection. Attempts DuckDB; if DuckDB fails, seamlessly falls back to SQLite (`sqlite3.Row` factory enabled).
  * **Input**: None.
  * **Output**: Open database connection object (`duckdb.DuckDBPyConnection` or `sqlite3.Connection`).

* **`execute(self, query: str, parameters: tuple = ()) -> Cursor`**
  * **Description**: Executes a parameterized SQL query under thread lock.
  * **Input**:
    * `query`: SQL string with `?` parameter markers.
    * `parameters`: Tuple of positional parameter values.
  * **Output**: Database cursor containing execution results.

* **`executemany(self, query: str, seq_of_parameters: list) -> Cursor`**
  * **Description**: Executes batch parameterized statements under thread lock.
  * **Input**:
    * `query`: SQL string with `?` parameter markers.
    * `seq_of_parameters`: List of tuples containing row parameters.
  * **Output**: Database cursor.

* **`fetchall(self, query: str, parameters: tuple = ()) -> list`**
  * **Description**: Executes query and fetches all matching rows.
  * **Input**:
    * `query`: SQL string.
    * `parameters`: Query parameter tuple.
  * **Output**: `list` of matching records.

* **`fetchone(self, query: str, parameters: tuple = ()) -> Any`**
  * **Description**: Executes query and returns the first row or `None`.
  * **Input**:
    * `query`: SQL string.
    * `parameters`: Query parameter tuple.
  * **Output**: A single row tuple/Row object, or `None`.

* **`commit(self) -> None`**
  * **Description**: Commits active transaction (SQLite only; DuckDB operates in auto-commit mode).
  * **Input**: None.
  * **Output**: `None`.

* **`close(self) -> None`**
  * **Description**: Closes the open database connection and resets instance state.
  * **Input**: None.
  * **Output**: `None`.

##### `get_db_connection() -> DatabaseConnection`
* **Description**: Returns the global singleton `DatabaseConnection` instance.
* **Input**: None.
* **Output**: `DatabaseConnection`.

##### `init_db(db: DatabaseConnection | None = None) -> None`
* **Description**: Creates core relational tables and indices if they do not exist:
  1. `entity_tags`: Tagged addresses, entity names, categories (`exchange`, `mixer`), sources, and confidence.
  2. `transaction_edges`: Directed edges (`tx_hash`, `source_address`, `target_address`, `amount_satoshis`, `timestamp`, `chain`, `is_coinbase`). Includes indices on `source_address` and `target_address`.
  3. `sahyog_dispatches`: Government Section 91 CrPC notice dispatch records.
  4. `investigation_cases`: Case metadata, suspect address, top VASP, confidence, and JSON results.
  5. `crawled_addresses`: Registry of addresses crawled from live APIs.
* **Input**: `db`: Optional `DatabaseConnection` instance (defaults to singleton).
* **Output**: `None`.

---

#### File: `backend/database/repositories.py`
Data Access Object (DAO) pattern implementations for all tables.

##### Class: `EntityTagRepository`
Interacts with the `entity_tags` table.

* **`__init__(self, db=None)`**
  * **Input**: `db`: Optional `DatabaseConnection`.
  * **Output**: Instance.

* **`upsert_tag(self, address: str, entity_name: str, category: str, chain: str = "BTC", source: str = "GraphSense", confidence: float = 1.0) -> None`**
  * **Description**: Inserts or replaces a tagged entity record.
  * **Input**: Address string, entity name, category, blockchain, data source, confidence score.
  * **Output**: `None`.

* **`bulk_insert_tags(self, tags: List[tuple]) -> None`**
  * **Description**: Performs batch insert of tag tuples.
  * **Input**: `tags`: List of tuples `(address, entity_name, category, chain, source, confidence)`.
  * **Output**: `None`.

* **`get_tag(self, address: str) -> Optional[Dict[str, Any]]`**
  * **Description**: Looks up entity tag for a single address.
  * **Input**: `address`: Wallet address string.
  * **Output**: `dict` containing tag fields or `None`.

* **`get_vasp_candidates_for_addresses(self, addresses: List[str]) -> List[Dict[str, Any]]`**
  * **Description**: Finds all addresses within the input list classified as `exchange`, `custodial`, or `vasp`.
  * **Input**: `addresses`: List of address strings.
  * **Output**: `list` of dicts `[{"address", "entity_name", "category", "confidence"}]`.

* **`list_all_vasp_addresses(self) -> List[str]`**
  * **Description**: Retrieves all known exchange/custodial wallet addresses in the registry.
  * **Input**: None.
  * **Output**: `List[str]` of wallet addresses.

---

##### Class: `TransactionEdgeRepository`
Interacts with `transaction_edges` and `crawled_addresses`.

* **`insert_edges(self, edges: List[tuple]) -> None`**
  * **Description**: Inserts transaction edge tuples, ignoring duplicate `(tx_hash, source, target)` keys.
  * **Input**: `edges`: List of tuples `(tx_hash, source_address, target_address, amount_satoshis, timestamp, chain, is_coinbase)`.
  * **Output**: `None`.

* **`get_connected_edges(self, address: str, limit: int = 100) -> List[Dict[str, Any]]`**
  * **Description**: Retrieves edges where `address` is either source or target, ordered by amount descending.
  * **Input**: `address: str`, `limit: int` (default `100`).
  * **Output**: `List[Dict[str, Any]]` with keys `tx_hash`, `source_address`, `target_address`, `amount_satoshis`, `timestamp`.

* **`get_outgoing_edges(self, address: str, limit: int = 100) -> List[Dict[str, Any]]`**
  * **Description**: Retrieves outgoing edges (`source_address = address`), sorted by volume descending.
  * **Input**: `address: str`, `limit: int`.
  * **Output**: `List[Dict[str, Any]]`.

* **`has_address_transactions(self, address: str) -> bool`**
  * **Description**: Checks if an address exists anywhere in the edges table.
  * **Input**: `address: str`.
  * **Output**: `bool`.

* **`is_address_crawled(self, address: str) -> bool`**
  * **Description**: Verifies if an address was already crawled via live APIs to prevent redundant HTTP requests.
  * **Input**: `address: str`.
  * **Output**: `bool`.

* **`mark_address_crawled(self, address: str, chain: str = "BTC") -> None`**
  * **Description**: Records that an address has been crawled in `crawled_addresses`.
  * **Input**: `address: str`, `chain: str`.
  * **Output**: `None`.

---

##### Class: `SahyogRepository`
Interacts with the `sahyog_dispatches` table.

* **`create_dispatch(self, ack_token: str, case_id: str, suspect_address: str, target_vasp: str, action: str, officer_name: str, jurisdiction: str, law_section: str, dispatch_hash: str, status: str = "SUBMITTED") -> None`**
  * **Description**: Inserts an official statutory dispatch notice record.
  * **Input**: Tracking token, case ID, suspect wallet, destination exchange, legal action, officer details, statutory section, SHA-256 hash, status.
  * **Output**: `None`.

* **`get_dispatch(self, ack_token: str) -> Optional[Dict[str, Any]]`**
  * **Description**: Fetches dispatch details by acknowledgment token.
  * **Input**: `ack_token: str`.
  * **Output**: `dict` of notice details or `None`.

---

##### Class: `CaseRepository`
Interacts with the `investigation_cases` table.

* **`save_case(self, case_id: str, suspect_address: str, top_vasp: str, confidence: float, results_data: dict) -> None`**
  * **Description**: Saves or updates an investigation case result with its full JSON results payload.
  * **Input**: Case ID, suspect address, top VASP name, confidence rating, result dictionary.
  * **Output**: `None`.

* **`get_case(self, case_id: str) -> Optional[Dict[str, Any]]`**
  * **Description**: Retrieves case record and deserializes the stored JSON results.
  * **Input**: `case_id: str`.
  * **Output**: `dict` or `None`.

* **`get_latest_case_by_suspect(self, suspect_address: str) -> Optional[Dict[str, Any]]`**
  * **Description**: Fetches the most recent case associated with a given suspect address.
  * **Input**: `suspect_address: str`.
  * **Output**: `dict` or `None`.

---

### C. Ingestion Subsystem

#### File: `backend/ingestion/schemas.py`

##### Class: `UniformEdge`
* **Description**: Immutable dataclass standardizing UTXO and Account-based transaction flows.
* **Fields**:
  * `source_address: str`
  * `target_address: str`
  * `amount_satoshis: int`
  * `tx_hash: str`
  * `timestamp: Optional[datetime]`
  * `chain: str = "BTC"`
  * `is_coinbase: bool = False`
* **Property: `amount_btc -> float`**: Computes `amount_satoshis / 100_000_000.0`.

##### Class: `EntityTagItem`
* **Description**: Immutable dataclass representing a verified entity label.
* **Fields**: `address: str`, `entity_name: str`, `category: str`, `chain: str = "BTC"`, `source: str = "GraphSense"`, `confidence: float = 1.0`.

---

#### File: `backend/ingestion/blockstream_client.py`
Implements a 3-tier live Bitcoin transaction fetcher with failover across Mempool.space, Blockstream Info, and Blockchain.info.

##### Class: `BlockstreamClient`

* **`__init__(self, base_url, fallback_url, repo, use_live_api)`**
  * **Input**: Base URL, fallback URL, optional `TransactionEdgeRepository`, `use_live_api` boolean.
  * **Output**: Configured client with connection pooling (`pool_connections=25`).

* **Property: `live_enabled -> bool`**
  * **Description**: Checks runtime configuration to determine if live API queries are allowed.
  * **Output**: `bool`.

* **`_get_with_failover(self, path: str) -> Optional[Any]`**
  * **Description**: Queries endpoints sequentially (Mempool -> Blockstream). Handles rate-limiting (HTTP 429 backoff) and non-existent addresses (HTTP 404 returns `[]`).
  * **Input**: `path: str` (e.g. `address/{addr}/txs`).
  * **Output**: Parsed JSON data or `None`.

* **`fetch_address_transactions(self, address: str) -> Optional[List[Dict[str, Any]]]`**
  * **Description**: Queries live transaction list for an address (capped at top 25).
  * **Input**: `address: str`.
  * **Output**: `List[dict]` of transactions or `None`.

* **`fetch_transaction_details(self, txid: str) -> Optional[Dict[str, Any]]`**
  * **Description**: Queries detailed transaction inputs and outputs for a specific txid.
  * **Input**: `txid: str`.
  * **Output**: `dict` or `None`.

* **`resolve_utxo_edges(self, tx_obj: dict) -> List[UniformEdge]`**
  * **Description**: Decomposes raw Bitcoin transaction inputs (`vin`) and outputs (`vout`) into `UniformEdge` instances using **Proportional UTXO Haircut allocation**:
    $$\text{allocated\_amount} = \text{round}\left(\text{vout\_value} \times \frac{\text{prevout\_val}[\text{src}]}{\text{total\_input\_val}}\right)$$
    Caps fan-out at 15 inputs and 15 outputs to eliminate combinatorial explosion from mining pools.
  * **Input**: `tx_obj: dict` (Raw transaction JSON).
  * **Output**: `List[UniformEdge]`.

* **`fetch_from_blockchain_info(self, address: str) -> List[UniformEdge]`**
  * **Description**: Third-tier fallback querying `blockchain.info/rawaddr/{address}` when Mempool and Blockstream fail.
  * **Input**: `address: str`.
  * **Output**: `List[UniformEdge]`.

* **`get_or_fetch_edges(self, address: str) -> List[UniformEdge]`**
  * **Description**: Core ingestion entrypoint:
    1. Checks if address was already crawled in local DB.
    2. Filters synthetic/demo addresses to remain offline.
    3. Fetches live data via failover chain if enabled.
    4. Inserts new edges into database.
    5. Marks address as crawled.
  * **Input**: `address: str`.
  * **Output**: `List[UniformEdge]`.

---

#### File: `backend/ingestion/etherscan_client.py`
Ethereum/EVM account-based transaction fetcher.

##### Class: `EtherscanClient`

* **`__init__(self, api_key, base_url, repo, use_live_api)`**
  * **Input**: API key, base URL, repository, live API flag.
  * **Output**: Instance.

* **Property: `live_enabled -> bool`**
  * **Output**: `bool`.

* **`fetch_account_transactions(self, address: str, limit: int = 50) -> List[Dict[str, Any]]`**
  * **Description**: Calls Etherscan `account.txlist` endpoint with retry backoff.
  * **Input**: `address: str`, `limit: int` (default `50`).
  * **Output**: `List[dict]` of raw transaction records.

* **`resolve_evm_edges(self, raw_txs: List[dict]) -> List[UniformEdge]`**
  * **Description**: Converts successful EVM transactions (`isError == "0"`) into `UniformEdge` objects, scaling Wei to normalized satoshi-equivalent units (`wei // 10_000_000_000`).
  * **Input**: `raw_txs: List[dict]`.
  * **Output**: `List[UniformEdge]`.

* **`get_or_fetch_edges(self, address: str) -> List[UniformEdge]`**
  * **Description**: Checks local cache, executes Etherscan fetch for EVM addresses (`0x...`), stores in DB, and returns outgoing edges.
  * **Input**: `address: str`.
  * **Output**: `List[UniformEdge]`.

---

#### File: `backend/ingestion/extractor.py`
Downstream Subgraph Extractor implementing bounded traversal with heuristic pruning.

##### Class: `SubgraphExtractor`

* **`__init__(self, db, tag_repo, edge_repo, btc_client, eth_client)`**
  * **Description**: Initializes extractor with repositories and network clients.
  * **Input**: Optional database and client instances.

* **`extract_subgraph(self, suspect_address: str, max_depth: int = DEFAULT_HOP_DEPTH, chain: str = "BTC") -> Tuple[nx.Graph, List[str], Dict[str, dict]]`**
  * **Description**: Traverses the transaction network starting from `suspect_address` using 3 key algorithms:
    1. **Directional Temporal Causality Filter**: Prunes downstream edges where timestamp $t_{\text{out}} < t_{\text{in}} - 2\text{h}$ (allowing 2-hour drift for Bitcoin block time variance).
    2. **High-Degree Super Hub Pruning**: If a non-suspect node has $\ge 45$ edges (e.g. mining pool or consolidation wallet), marks it as `suspected_hub` and halts deeper expansion.
    3. **Adaptive Cumulative Volume Beam Search**: Accumulates candidate outgoing branches until $\ge 85\%$ of total candidate volume is captured (bounded between $3$ and $12$ branches), preventing combinatorial explosion while preserving peel chains.
    4. **Dirichlet Boundary Halting**: Stops traversal whenever a known VASP boundary node is reached.
  * **Input**:
    * `suspect_address: str`: Seed address under investigation.
    * `max_depth: int`: Traversal depth limit (hops).
    * `chain: str`: Network (`BTC` or `ETH`).
  * **Output**: `Tuple[nx.Graph, List[str], Dict[str, dict]]`:
    * `G (nx.Graph)`: Weighted undirected NetworkX graph where weights represent transaction volume.
    * `candidate_vasps`: List of discovered VASP wallet addresses.
    * `node_metadata`: Map of address to attributes (`role`, `label`, `entity`, `category`).

---

#### File: `backend/ingestion/elliptic_loader.py`
Ingestion loader for the academic Elliptic / Elliptic++ Anti-Money Laundering benchmark dataset.

##### Class: `EllipticLoader`

* **`__init__(self, tag_repo, edge_repo)`**
  * **Input**: Repositories.

* **`ingest_classes(self, classes_csv_path: Path) -> int`**
  * **Description**: Reads `txClasses.csv` and maps Class 1 (illicit) to `mixer` category and Class 2 (licit) to `exchange` category in `entity_tags`.
  * **Input**: Path to CSV file.
  * **Output**: `int` (Number of tags inserted).

* **`ingest_edgelist(self, edgelist_csv_path: Path, default_weight: int = 10_000_000) -> int`**
  * **Description**: Reads `txEdgeList.csv` (`txId1 -> txId2`) and loads edges into `transaction_edges`.
  * **Input**: Path to CSV file, default weight in satoshis.
  * **Output**: `int` (Number of edges inserted).

* **`generate_and_ingest_sample(self, num_nodes: int = 40) -> Tuple[int, int]`**
  * **Description**: Bundles and seeds an authentic Elliptic++ reference benchmark scenario featuring an illicit syndicate (`tx_101`), 3 parallel mixer hubs (`tx_102`, `tx_103`, `tx_104`), a true regulated exchange (`tx_201`), and a low-volume decoy exchange (`tx_202`).
  * **Input**: `num_nodes: int` (default 40).
  * **Output**: `Tuple[int, int]` `(tags_count, edges_count)`.

---

#### File: `backend/ingestion/tagpack_loader.py`
Parses and loads GraphSense TagPacks and Crypto-Tags registries.

##### `parse_simple_yaml(text: str) -> List[dict]`
* **Description**: Zero-dependency lightweight YAML parser that extracts `tags` blocks with `address`, `label`, and `category` when PyYAML is unavailable.
* **Input**: `text: str` (Raw YAML string).
* **Output**: `List[dict]`.

##### Class: `TagPackLoader`

* **`__init__(self, repo)`**
  * **Input**: Optional `EntityTagRepository`.

* **`sanitize_and_validate(self, record: dict) -> Optional[tuple]`**
  * **Description**: Validates address format via `validate_crypto_address`, standardizes categories (`exchange`, `mixer`, `illicit`), and returns sanitized record tuple.
  * **Input**: `record: dict`.
  * **Output**: `tuple` `(address, entity_name, category, chain, source, confidence)` or `None`.

* **`load_from_text(self, content: str, filename: str = "data.json") -> int`**
  * **Description**: Ingests tagpack from string (detects JSON, YAML, or CSV by filename extension).
  * **Input**: File content string, filename string.
  * **Output**: `int` (Valid tags inserted).

* **`load_from_file(self, file_path: Path) -> int`**
  * **Description**: Ingests tagpack directly from a local filesystem path.
  * **Input**: `file_path: Path`.
  * **Output**: `int`.

* **`fetch_remote_tagpack(self, url: str) -> int`**
  * **Description**: Fetches raw TagPack from remote HTTP URL (e.g. GitHub raw) and loads into database.
  * **Input**: `url: str`.
  * **Output**: `int`.

* **`load_all_bundled_tagpacks(self) -> int`**
  * **Description**: Scans `backend/ingestion/tagpacks/` and ingests all bundled JSON, YAML, and CSV files.
  * **Input**: None.
  * **Output**: `int` (Total tags ingested).

---

#### File: `backend/ingestion/seed_demo.py`
Synthesizes test graphs and offline laundering scenarios.

##### `generate_fake_tx_hash(src: str, dst: str, nonce: int) -> str`
* **Description**: Generates deterministic SHA-256 hash for simulated transactions.
* **Input**: `src: str`, `dst: str`, `nonce: int`.
* **Output**: `str` (64-character hex hash).

##### `seed_database(num_cases: int = 25) -> None`
* **Description**: Populates the database with:
  1. Bundled GraphSense and Crypto-Tags registries.
  2. Elliptic++ AML benchmark dataset.
  3. Scenario 0: Frozen contract validation case from `docs/ENGINE_CONTRACT.md`.
  4. Scenario 1: Famous Genesis laundering case (`1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa` -> 6 parallel mixer channels -> Binance).
  5. Scenarios 2 to `num_cases`: 23 procedural laundering graphs alternating between multi-hop peel chains and high-entropy mixer splits.
* **Input**: `num_cases: int` (default `25`).
* **Output**: `None`.

---

#### File: `backend/ingestion/fetch_datasets.py`
Standalone CLI management script for triggering ingestion.

##### `fetch_vasp_tags(repo: EntityTagRepository) -> None`
* **Description**: Ingests local bundled tagpacks and attempts remote GitHub fetching.
* **Input**: `EntityTagRepository`.
* **Output**: `None`.

##### `fetch_elliptic_dataset(tag_repo: EntityTagRepository, edge_repo: TransactionEdgeRepository, path: str | None = None) -> None`
* **Description**: Ingests Elliptic++ dataset from path or loads the built-in reference benchmark.
* **Input**: Repositories, optional local CSV directory path.
* **Output**: `None`.

##### `query_live_bitcoin(address: str, repo: TransactionEdgeRepository) -> None`
* **Description**: CLI test querying and printing live Bitcoin transactions for an address.
* **Input**: Address string, repository.
* **Output**: `None`.

##### `query_live_ethereum(address: str, repo: TransactionEdgeRepository) -> None`
* **Description**: CLI test querying and printing live Ethereum transactions for an EVM address.
* **Input**: Address string, repository.
* **Output**: `None`.

##### `main() -> None`
* **Description**: CLI argument parser supporting `--all`, `--tags`, `--elliptic [path]`, `--live-btc <addr>`, and `--live-eth <addr>`.
* **Input**: Command-line arguments (`sys.argv`).
* **Output**: `None`.

---

### D. Pydantic Models & Validation

#### File: `backend/models/common.py`
##### `validate_crypto_address(val: str) -> str`
* **Description**: Validates address against Bitcoin Base58 regex (`^[13]...`), Bitcoin Bech32 regex (`^bc1...`), EVM regex (`^0x[a-fA-F0-9]{40}$`), or synthetic demo prefixes (`suspect_*`, `VASP_*`, `mixer_*`, `peel_*`, `tx_*`).
* **Input**: `val: str`.
* **Output**: `str` (Trimmed address) or raises `ValueError`.

##### `CryptoAddress`
* **Description**: Annotated Pydantic type with `BeforeValidator(validate_crypto_address)`.

---

#### File: `backend/models/attribution.py`
* **`InvestigateRequest`**: Primary investigation payload (`suspect_address: CryptoAddress`, `chain: str = "BTC"`, `depth_limit: int = 4`, `candidate_vasps: Optional[List[str]]`).
* **`RankedVaspItem`**: Individual attribution result (`vasp_name: str`, `candidate_address: str`, `effective_resistance: float`, `confidence_score: float`).
* **`GraphSummary`**: Graph computational metrics (`nodes_analyzed: int`, `edges_analyzed: int`, `compute_time_ms: float`, `solver_method: str = "effective_resistance"`).
* **`InvestigateResponse`**: Complete response payload (`case_id: Optional[str]`, `suspect_address: str`, `ranked_vasps: List[RankedVaspItem]`, `graph_summary: GraphSummary`).
* **`AttributionRequest` & `AttributionResponse`**: Backwards-compatibility schemas conforming to `ENGINE_CONTRACT.md`.

---

#### File: `backend/models/graph.py`
* **`CytoscapeNodeData` & `CytoscapeNode`**: Node representation for Cytoscape.js (`id`, `label`, `role: "suspect" | "mixer_hop" | "candidate_vasp" | "hop" | "background"`, `entity`, `category`).
* **`CytoscapeEdgeData` & `CytoscapeEdge`**: Edge representation (`id: "u->v"`, `source`, `target`, `weight`, `amount_satoshis`, `tx_hash`).
* **`SubgraphResponse`**: Top-level graph payload containing `nodes: List[CytoscapeNode]`, `edges: List[CytoscapeEdge]`, and `stats: dict`.

---

#### File: `backend/models/reports.py`
* **`ReportMetadata`**: Case metadata for report header.
* **`ReportExportResponse`**: File export confirmation metadata (`case_id`, `filename`, `content_type`, `file_size_bytes`).

---

#### File: `backend/models/sahyog.py`
* **`SahyogDispatchRequest`**: Input for lawful freeze notice (`case_id`, `suspect_address`, `target_vasp`, `action`, `officer_name`, `jurisdiction`, `law_section`).
* **`SahyogDispatchResponse`**: Acknowledgment payload (`ack_token`, `case_id`, `suspect_address`, `target_vasp`, `action`, `status: "SUBMITTED"`, `timestamp`, `dispatch_hash`, `vasp_compliance_portal`).

---

### E. Services Subsystem

#### File: `backend/services/attribution_service.py`
Orchestrates subgraph extraction, candidate identification, Laplacian solving, and confidence scoring.

##### Class: `AttributionService`

* **`__init__(self, extractor, tag_repo, case_repo)`**
  * **Input**: Optional instances of `SubgraphExtractor`, `EntityTagRepository`, and `CaseRepository`.
  * **Output**: Instance.

* **`investigate(self, req: InvestigateRequest) -> InvestigateResponse`**
  * **Description**:
    1. Calls `extractor.extract_subgraph()` to generate the $k$-hop neighborhood graph.
    2. Resolves candidate VASPs from: explicit request candidates $\rightarrow$ discovered graph tags $\rightarrow$ all repository VASPs in graph $\rightarrow$ dynamic fallback to top-conductance recipient hubs.
    3. Instantiates `src.attribution.engine.AttributionEngine(graph, weight_attr="weight")` and executes `engine.attribute(suspect, candidates)`.
    4. Normalizes effective resistance ($R_{\text{eff}}$) into probabilistic confidence scores via inverse conductance weighting:
       $$\text{weight}_i = \frac{1}{R_{\text{eff}, i} + 10^{-6}}, \quad \text{confidence}_i = \frac{\text{weight}_i}{\sum \text{weight}}$$
    5. Generates unique audit `case_id` (`CASE-<SUSPECT_PREFIX>-<TIMESTAMP>`).
    6. Persists the case in `investigation_cases` table.
    7. Returns structured `InvestigateResponse`.
  * **Input**: `req: InvestigateRequest`.
  * **Output**: `InvestigateResponse`.
  * **Errors Raised**: `ValueError` if suspect has no transaction history or no reachable candidates exist.

---

#### File: `backend/services/graph_service.py`
Translates extracted NetworkX graphs into frontend visualization schemas.

##### Class: `GraphService`

* **`__init__(self, extractor: Optional[SubgraphExtractor] = None)`**
  * **Input**: Optional `SubgraphExtractor`.

* **`get_cytoscape_subgraph(self, suspect_address: str, max_depth: int = 3, chain: str = "BTC") -> SubgraphResponse`**
  * **Description**: Calls `SubgraphExtractor.extract_subgraph`, maps each NetworkX node into `CytoscapeNode` with role styling (`suspect`, `mixer_hop`, `candidate_vasp`, `background`), maps each edge into `CytoscapeEdge` with satoshi amounts and weights, and computes graph summary statistics.
  * **Input**: `suspect_address: str`, `max_depth: int = 3`, `chain: str = "BTC"`.
  * **Output**: `SubgraphResponse`.

---

#### File: `backend/services/sahyog_service.py`
Simulates statutory notices sent to Indian VASP compliance portals.

##### Class: `SahyogService`

* **`__init__(self, repo: Optional[SahyogRepository] = None)`**
  * **Input**: Optional `SahyogRepository`.

* **`dispatch_notice(self, req: SahyogDispatchRequest) -> SahyogDispatchResponse`**
  * **Description**:
    1. Generates unique tracking token: `SAHYOG-ACK-2026-<HEX6>`.
    2. Computes SHA-256 audit hash: $\text{SHA256}(\text{case\_id} : \text{suspect} : \text{vasp} : \text{action} : \text{timestamp})$.
    3. Persists dispatch record in `sahyog_dispatches` table.
    4. Returns `SahyogDispatchResponse` with mock compliance portal URL.
  * **Input**: `req: SahyogDispatchRequest`.
  * **Output**: `SahyogDispatchResponse`.

* **`get_dispatch_status(self, ack_token: str) -> Optional[dict]`**
  * **Description**: Fetches existing dispatch from repository and constructs the compliance portal link.
  * **Input**: `ack_token: str`.
  * **Output**: `Optional[dict]`.

---

#### File: `backend/services/report_service.py`
Generates court-admissible forensic incident dossiers compliant with Section 65B of the Indian Evidence Act.

##### Class: `ReportService`

* **`__init__(self, case_repo: Optional[CaseRepository] = None)`**
  * **Input**: Optional `CaseRepository`.

* **`generate_pdf_report(self, case_id: str) -> io.BytesIO`**
  * **Description**:
    1. Queries case details from `CaseRepository` by `case_id` or suspect address.
    2. Builds formatted PDF in an in-memory `BytesIO` buffer via ReportLab (with fallback text emulation if ReportLab is missing).
    3. Sections included:
       - Header: Cyber Crime Forensic Intelligence Dossier banner.
       - Case Meta Box: Case reference, generation timestamp, network, top attributed VASP, and confidence percentage.
       - Executive Summary: Contextual breakdown of $Lx = b$ effective resistance calculation.
       - Candidate VASP Attribution Matrix: Ranked table showing entity names, masked addresses, $R_{\text{eff}}$ values, and confidence.
       - Graph Computation Metrics: Node count, edge count, solver execution time, and method.
       - Section 65B Indian Evidence Act Certificate: Cryptographic verification statement with SHA-256 hash.
       - Signature Blocks: Lines for Investigating Officer and Digital Forensics Lead.
  * **Input**: `case_id: str`.
  * **Output**: `io.BytesIO` positioned at byte 0 ready for streaming.
  * **Errors Raised**: `ValueError` if case is not found.

---

#### File: `backend/services/project_report_generator.py`
Compiles an exhaustive, multi-page technical report describing the mathematical breakthroughs, benchmarks, and architecture of the SIH26182 platform.

##### Class: `NumberedCanvas(canvas.Canvas)`
* **Description**: Two-pass ReportLab canvas that calculates total page count dynamically to render "Page X of Y", confidential headers, and footer divider lines.
* **Methods**:
  * `showPage(self)`: Records page state dictionary.
  * `save(self)`: Iterates through saved page states and invokes `draw_page_decorations(page_count)`.
  * `draw_page_decorations(self, page_count: int)`: Renders top header rule and bottom confidentiality text.

##### `build_project_implementation_pdf(output_stream: io.BytesIO) -> None`
* **Description**: Builds a 5-6 page comprehensive PDF report with custom typography, problem analysis, circuit physics mathematics, multi-tier ingestion architecture, empirical benchmark tables, and law enforcement integrations.
* **Input**: `output_stream: io.BytesIO`.
* **Output**: `None` (Writes directly to stream).

##### `generate_pdf_file(target_path: Path) -> str`
* **Description**: Wrapper that generates the project report and writes it to a file on disk.
* **Input**: `target_path: Path`.
* **Output**: `str` (Path string of generated PDF).

---

### F. API Routers

#### File: `backend/routers/investigate.py`
Mounted at root (`tags=["Attribution & Investigation"]`).

##### `investigate_wallet(req: InvestigateRequest) -> InvestigateResponse`
* **HTTP Route**: `POST /api/v1/investigate`
* **Description**: Primary investigation endpoint. Traverses $k$-hop neighborhood, identifies candidate VASPs, solves $Lx = b$, normalizes confidence scores, persists case, and returns results.
* **Input**: `req: InvestigateRequest` (JSON body).
* **Output**: `InvestigateResponse` (HTTP 200).
* **HTTP Errors**:
  * `400 Bad Request`: Validation failure or empty parameters.
  * `404 Not Found`: Wallet has no transaction history in the graph.
  * `500 Internal Server Error`: Unexpected solver failure.

##### `attribute_frozen_contract(req: AttributionRequest) -> AttributionResponse`
* **HTTP Route**: `POST /attribute`
* **Description**: Legacy frozen contract endpoint matching `docs/ENGINE_CONTRACT.md`. Accepts `{ suspect_wallet, candidate_vasps }` and returns `{ suspect, ranked_candidates, scores, method }`.
* **Input**: `req: AttributionRequest` (JSON body).
* **Output**: `AttributionResponse` (HTTP 200).
* **HTTP Errors**: `400`, `404`, `500`.

---

#### File: `backend/routers/graph.py`
Mounted with prefix `/api/v1/graph` (`tags=["Graph Visualizations"]`).

##### `get_address_subgraph(address: str, depth: int = Query(3), chain: str = Query("BTC")) -> SubgraphResponse`
* **HTTP Route**: `GET /api/v1/graph/subgraph/{address}`
* **Description**: Returns graph nodes and edges formatted for direct Cytoscape.js or D3.js rendering, including entity metadata and node roles (`suspect`, `mixer_hop`, `candidate_vasp`, `background`).
* **Input**:
  * `address: str` (Path parameter): Target wallet address.
  * `depth: int` (Query parameter, range 1-10, default 3): Hops limit.
  * `chain: str` (Query parameter, default "BTC"): Target blockchain.
* **Output**: `SubgraphResponse` (HTTP 200).
* **HTTP Errors**:
  * `400 Bad Request`: Malformed cryptocurrency address.
  * `404 Not Found`: No transaction subgraph discovered for address.
  * `500 Internal Server Error`: Subgraph extraction failure.

---

#### File: `backend/routers/sahyog.py`
Mounted with prefix `/api/v1/sahyog` (`tags=["SAHYOG Lawful Dispatcher"]`).

##### `dispatch_lawful_notice(req: SahyogDispatchRequest) -> SahyogDispatchResponse`
* **HTTP Route**: `POST /api/v1/sahyog/dispatch`
* **Description**: Submits statutory Section 91 CrPC notice to target VASP, records SHA-256 audit hash, and returns government tracking token.
* **Input**: `req: SahyogDispatchRequest` (JSON body).
* **Output**: `SahyogDispatchResponse` (HTTP 200).
* **HTTP Errors**: `500 Internal Server Error`.

##### `get_dispatch_details(ack_token: str) -> dict`
* **HTTP Route**: `GET /api/v1/sahyog/{ack_token}`
* **Description**: Retrieves audit details and compliance status for a previously issued SAHYOG notice.
* **Input**: `ack_token: str` (Path parameter).
* **Output**: `dict` containing dispatch details (HTTP 200).
* **HTTP Errors**: `404 Not Found` if token does not exist in registry.

---

#### File: `backend/routers/reports.py`
Mounted with prefix `/api/v1/reports` (`tags=["Forensic Reports"]`).

##### `export_project_overview_report() -> StreamingResponse`
* **HTTP Route**: `GET /api/v1/reports/project-overview/export`
* **Description**: Builds and streams the comprehensive multi-page PDF project architecture and implementation report (`SIH26182_Project_Implementation_Report.pdf`), while also caching a copy in the project root.
* **Input**: None.
* **Output**: `StreamingResponse` (media type `application/pdf`, filename `SIH26182_Project_Implementation_Report.pdf`).
* **HTTP Errors**: `500 Internal Server Error`.

##### `export_case_report(case_id: str) -> StreamingResponse`
* **HTTP Route**: `GET /api/v1/reports/{case_id}/export`
* **Description**: Generates and streams a court-admissible LEA-style forensic PDF report certified under Section 65B of the Indian Evidence Act.
* **Input**: `case_id: str` (Path parameter).
* **Output**: `StreamingResponse` (media type `application/pdf`, filename `Forensic_Report_{case_id}.pdf`).
* **HTTP Errors**:
  * `404 Not Found`: Case reference or suspect not found.
  * `500 Internal Server Error`: Generation failure.

---

## 4. Test Suite Summary

The backend includes 8 dedicated pytest test suites located in `backend/tests/`:

| Test Module | Coverage & Functions Tested |
| :--- | :--- |
| `test_investigate_api.py` | Validates `POST /api/v1/investigate` and legacy `POST /attribute`, tests confidence score normalization, and validates 404 handling. |
| `test_blockstream.py` | Tests Blockstream and Mempool client connection pooling, UTXO edge resolution, and haircut allocation. |
| `test_extractor.py` | Tests SubgraphExtractor temporal causality filtering, beam search volume thresholds, and hub pruning. |
| `test_tagpack_loader.py` | Validates GraphSense YAML, JSON, and CSV parsing, regex address validation, and category mapping. |
| `test_sahyog_dispatch.py` | Tests SAHYOG notice submission, SHA-256 dispatch hashing, database persistence, and lookup. |
| `test_report_export.py` | Validates in-memory ReportLab PDF generation, Section 65B text inclusion, and table rendering. |
| `test_db.py` | Tests DuckDB connection, automatic SQLite fallback, table initialization, and index creation. |
| `test_ingestion_sources.py` | Tests multi-tier failover from Mempool to Blockstream to Blockchain.info. |

---

## 5. Input & Output Quick Reference Table

| Function / Endpoint | Input Type | Output Type |
| :--- | :--- | :--- |
| `POST /api/v1/investigate` | `InvestigateRequest` | `InvestigateResponse` |
| `POST /attribute` | `AttributionRequest` | `AttributionResponse` |
| `GET /api/v1/graph/subgraph/{address}` | `address: str`, `depth: int`, `chain: str` | `SubgraphResponse` |
| `POST /api/v1/sahyog/dispatch` | `SahyogDispatchRequest` | `SahyogDispatchResponse` |
| `GET /api/v1/sahyog/{ack_token}` | `ack_token: str` | `dict` |
| `GET /api/v1/reports/{case_id}/export` | `case_id: str` | `StreamingResponse (PDF)` |
| `GET /api/v1/reports/project-overview/export` | None | `StreamingResponse (PDF)` |
| `GET /health` | None | `dict` |
| `AttributionService.investigate` | `InvestigateRequest` | `InvestigateResponse` |
| `GraphService.get_cytoscape_subgraph` | `address: str`, `max_depth: int`, `chain: str` | `SubgraphResponse` |
| `SahyogService.dispatch_notice` | `SahyogDispatchRequest` | `SahyogDispatchResponse` |
| `ReportService.generate_pdf_report` | `case_id: str` | `io.BytesIO` |
| `SubgraphExtractor.extract_subgraph` | `suspect_address: str`, `max_depth: int`, `chain: str` | `Tuple[nx.Graph, List[str], Dict[str, dict]]` |
| `BlockstreamClient.get_or_fetch_edges` | `address: str` | `List[UniformEdge]` |
| `BlockstreamClient.resolve_utxo_edges` | `tx_obj: dict` | `List[UniformEdge]` |
| `EtherscanClient.get_or_fetch_edges` | `address: str` | `List[UniformEdge]` |
| `EtherscanClient.resolve_evm_edges` | `raw_txs: List[dict]` | `List[UniformEdge]` |
| `TagPackLoader.load_from_text` | `content: str`, `filename: str` | `int` (Tag count) |
| `TagPackLoader.sanitize_and_validate` | `record: dict` | `Optional[tuple]` |
| `EllipticLoader.ingest_classes` | `classes_csv_path: Path` | `int` (Inserted count) |
| `EllipticLoader.ingest_edgelist` | `edgelist_csv_path: Path`, `default_weight: int` | `int` (Inserted count) |
| `DatabaseConnection.execute` | `query: str`, `parameters: tuple` | `Cursor` |
| `DatabaseConnection.fetchall` | `query: str`, `parameters: tuple` | `list` |
| `DatabaseConnection.fetchone` | `query: str`, `parameters: tuple` | `Any` |
| `validate_crypto_address` | `val: str` | `str` |
