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

# Load .env if present
for env_path in [PROJECT_ROOT / ".env", BACKEND_DIR / ".env"]:
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip('"\'')
                    if k not in os.environ:
                        os.environ[k] = v

# Runtime Flags
USE_LIVE_API = os.getenv("USE_LIVE_API", "true").lower() in ("true", "1", "yes")

# External APIs
BLOCKSTREAM_BASE_URL = os.getenv("BLOCKSTREAM_BASE_URL", "https://mempool.space/api")
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "6"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "1"))

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
