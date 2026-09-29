"""
API entrypoint inside backend.
Wraps the FastAPI app with the full ingestion and attribution orchestration pipeline.
"""
from backend.main import app

__all__ = ["app"]
