from fastapi import APIRouter
from app.db.session import engine
from app.core.config import settings
import asyncio
from sqlalchemy import text

try:
    from redis import asyncio as aioredis
except Exception:
    aioredis = None

try:
    from app.retrieval.qdrant_client import client as qdrant_client
except Exception:
    qdrant_client = None

router = APIRouter(prefix="/health")

@router.get("/")
async def health():
    status = {"status": "ok", "components": {}}
    # Postgres
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        status["components"]["postgres"] = "ok"
    except Exception as e:
        status["components"]["postgres"] = f"error: {e}"
    # Redis
    try:
        if aioredis:
            r = await aioredis.from_url(settings.REDIS_URL)
            await r.ping()
            status["components"]["redis"] = "ok"
        else:
            status["components"]["redis"] = "unavailable"
    except Exception as e:
        status["components"]["redis"] = f"error: {e}"
    # Qdrant
    try:
        if qdrant_client and qdrant_client.client:
            status["components"]["qdrant"] = "ok"
        else:
            status["components"]["qdrant"] = "unavailable"
    except Exception as e:
        status["components"]["qdrant"] = f"error: {e}"
    return status
