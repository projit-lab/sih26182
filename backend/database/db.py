import logging
import sqlite3
import threading
from typing import Any
from pathlib import Path

from backend.config import DB_PATH, SQLITE_DB_PATH

logger = logging.getLogger(__name__)

# Check if duckdb is installed
try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False
    logger.warning("duckdb package not found. Falling back to sqlite3 for local storage.")


class DatabaseConnection:
    """
    Unified database interface supporting DuckDB with graceful SQLite fallback.
    Both support standard SQL queries and '?' parameter markers.
    Thread-safe across parallel ingestion workers via RLock.
    """

    def __init__(self, db_path: Path = DB_PATH, use_duckdb: bool = HAS_DUCKDB):
        self.db_path = db_path
        self.use_duckdb = use_duckdb
        self._conn = None
        self._lock = threading.RLock()

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
                    logger.error(f"Failed to connect to DuckDB: {e}. Falling back to SQLite.")
                    self.use_duckdb = False

            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            return self._conn

    def execute(self, query: str, parameters: tuple = ()):
        with self._lock:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute(query, parameters)
            return cursor

    def executemany(self, query: str, seq_of_parameters: list):
        with self._lock:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.executemany(query, seq_of_parameters)
            return cursor

    def fetchall(self, query: str, parameters: tuple = ()) -> list:
        with self._lock:
            cursor = self.execute(query, parameters)
            if hasattr(cursor, "fetchall"):
                rows = cursor.fetchall()
                # If duckdb, rows might be tuples or numpy arrays
                return rows
            return []

    def fetchone(self, query: str, parameters: tuple = ()) -> Any:
        with self._lock:
            cursor = self.execute(query, parameters)
            if hasattr(cursor, "fetchone"):
                return cursor.fetchone()
            return None

    def commit(self):
        with self._lock:
            if self._conn is not None and not self.use_duckdb:
                self._conn.commit()

    def close(self):
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None


# Singleton connection
_db_instance: DatabaseConnection | None = None


def get_db_connection() -> DatabaseConnection:
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseConnection()
        _db_instance.connect()
    return _db_instance


def init_db(db: DatabaseConnection | None = None):
    """
    Initialize required tables and indexes in DuckDB / SQLite.
    """
    if db is None:
        db = get_db_connection()

    # 1. entity_tags table
    db.execute("""
        CREATE TABLE IF NOT EXISTS entity_tags (
            address VARCHAR PRIMARY KEY,
            entity_name VARCHAR NOT NULL,
            category VARCHAR NOT NULL,
            chain VARCHAR DEFAULT 'BTC',
            source VARCHAR DEFAULT 'GraphSense',
            confidence DOUBLE DEFAULT 1.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. transaction_edges table
    db.execute("""
        CREATE TABLE IF NOT EXISTS transaction_edges (
            tx_hash VARCHAR NOT NULL,
            source_address VARCHAR NOT NULL,
            target_address VARCHAR NOT NULL,
            amount_satoshis BIGINT NOT NULL,
            timestamp TIMESTAMP,
            chain VARCHAR DEFAULT 'BTC',
            is_coinbase BOOLEAN DEFAULT FALSE,
            PRIMARY KEY (tx_hash, source_address, target_address)
        );
    """)

    # Indexes on transaction_edges
    try:
        db.execute("CREATE INDEX IF NOT EXISTS idx_tx_source ON transaction_edges(source_address);")
        db.execute("CREATE INDEX IF NOT EXISTS idx_tx_target ON transaction_edges(target_address);")
    except Exception as e:
        logger.debug(f"Index creation note: {e}")

    # 3. sahyog_dispatches table
    db.execute("""
        CREATE TABLE IF NOT EXISTS sahyog_dispatches (
            ack_token VARCHAR PRIMARY KEY,
            case_id VARCHAR NOT NULL,
            suspect_address VARCHAR NOT NULL,
            target_vasp VARCHAR NOT NULL,
            action VARCHAR NOT NULL,
            officer_name VARCHAR,
            jurisdiction VARCHAR,
            law_section VARCHAR DEFAULT 'Section 91 CrPC',
            dispatch_hash VARCHAR,
            status VARCHAR DEFAULT 'SUBMITTED',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 4. investigation_cases table
    db.execute("""
        CREATE TABLE IF NOT EXISTS investigation_cases (
            case_id VARCHAR PRIMARY KEY,
            suspect_address VARCHAR NOT NULL,
            top_vasp VARCHAR NOT NULL,
            confidence DOUBLE NOT NULL,
            results_json VARCHAR NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 5. crawled_addresses table
    db.execute("""
        CREATE TABLE IF NOT EXISTS crawled_addresses (
            address VARCHAR PRIMARY KEY,
            chain VARCHAR DEFAULT 'BTC',
            crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    db.commit()
    logger.info("Database initialized successfully.")
