import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.db.session import init_db, close_db
from app.api import health, ingest, query
from app.cache.rate_limit import RateLimitMiddleware
from app.core.logging import setup_logging
from app.retrieval.bm25 import store as bm25_store
from app.retrieval.qdrant_client import client as qdrant_client

setup_logging()

app = FastAPI(title="legal-rag")

# Register routers
app.include_router(health.router)
app.include_router(ingest.router)
app.include_router(query.router)

# Prometheus instrumentation
Instrumentator().instrument(app).expose(app)

@app.on_event("startup")
async def startup_event():
    # Initialize DB (create tables if missing)
    await init_db()
    # Build BM25 index from Qdrant for demo tenant
    if qdrant_client.client:
        try:
            bm25_store.build_from_qdrant("00000000-0000-0000-0000-000000000001", qdrant_client)
        except Exception as e:
            print(f"Failed to build BM25 index on startup: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    await close_db()
