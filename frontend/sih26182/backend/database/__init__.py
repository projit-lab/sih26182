"""
Database package for DuckDB / SQLite relational storage.
"""
from backend.database.db import get_db_connection, init_db

__all__ = ["get_db_connection", "init_db"]
