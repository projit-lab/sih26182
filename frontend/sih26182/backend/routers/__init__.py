"""
Routers package for API v1 endpoints.
"""
from backend.routers.investigate import router as investigate_router
from backend.routers.graph import router as graph_router
from backend.routers.sahyog import router as sahyog_router
from backend.routers.reports import router as reports_router

__all__ = [
    "investigate_router",
    "graph_router",
    "sahyog_router",
    "reports_router",
]
