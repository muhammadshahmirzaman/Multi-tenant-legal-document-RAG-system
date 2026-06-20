import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.db.session import init_db, close_db
from app.api import health, ingest, query
from app.cache.rate_limit import RateLimitMiddleware
from app.core.logging import setup_logging

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

@app.on_event("shutdown")
async def shutdown_event():
    await close_db()
