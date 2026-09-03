import os
from pathlib import Path

# Base Paths
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database
DB_PATH = DATA_DIR / "attribution.duckdb"
SQLITE_DB_PATH = DATA_DIR / "attribution.sqlite"

# Runtime Flags
USE_LIVE_API = os.getenv("USE_LIVE_API", "false").lower() in ("true", "1", "yes")

# External APIs
BLOCKSTREAM_BASE_URL = os.getenv("BLOCKSTREAM_BASE_URL", "https://blockstream.info/api")
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# Graph Search Limits
DEFAULT_HOP_DEPTH = int(os.getenv("DEFAULT_HOP_DEPTH", "3"))
MAX_HOP_DEPTH = int(os.getenv("MAX_HOP_DEPTH", "6"))
MAX_SUBGRAPH_NODES = int(os.getenv("MAX_SUBGRAPH_NODES", "2000"))

# CORS settings for Frontend connection
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "*",
]
