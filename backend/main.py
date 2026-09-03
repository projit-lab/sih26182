import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import CORS_ORIGINS, USE_LIVE_API
from backend.database.db import get_db_connection, init_db
from backend.database.repositories import EntityTagRepository, TransactionEdgeRepository
from backend.ingestion.seed_demo import seed_database
from backend.routers.investigate import router as investigate_router
from backend.routers.graph import router as graph_router
from backend.routers.sahyog import router as sahyog_router
from backend.routers.reports import router as reports_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("backend.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database is initialized and seeded
    logger.info("Initializing SIH26182 Backend Engine...")
    db = get_db_connection()
    init_db(db)

    # Automatically seed demo cases if database is empty
    tag_repo = EntityTagRepository(db)
    edge_repo = TransactionEdgeRepository(db)
    if not tag_repo.list_all_vasp_addresses():
        logger.info("Empty database detected. Seeding offline demo dataset and GraphSense tags...")
        seed_database(num_cases=25)

    logger.info(f"SIH26182 Engine Ready (USE_LIVE_API={USE_LIVE_API}).")
    yield
    # Shutdown
    logger.info("Shutting down backend services.")


app = FastAPI(
    title="SIH26182 - Wallet-to-VASP Attribution & Ingestion Engine",
    description=(
        "Production backend orchestration layer connecting on-chain UTXO data and "
        "the Core Laplacian Solver (Lx = b) to the UI, Mock SAHYOG dispatcher, "
        "and Section 65B PDF reporting pipeline."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(investigate_router)
app.include_router(graph_router)
app.include_router(sahyog_router)
app.include_router(reports_router)


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": "SIH26182 Backend & Ingestion Layer",
        "version": "1.0.0",
        "use_live_api": USE_LIVE_API,
    }


@app.get("/", tags=["System"])
def root():
    return {
        "message": "Welcome to SIH26182 Wallet Attribution API",
        "docs_url": "/docs",
        "health_url": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
