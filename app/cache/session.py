from typing import List
from app.core.config import settings

try:
    from redis import asyncio as aioredis
    HAS_REDIS = True
except Exception:
    aioredis = None
    HAS_REDIS = False


async def push_message(session_id: str, message: str):
    if not HAS_REDIS:
        return False
    r = await aioredis.from_url(settings.REDIS_URL)
    key = f"session:{session_id}:history"
    await r.lpush(key, message)
    await r.ltrim(key, 0, 9)
    await r.expire(key, 1800)
    return True


async def get_history(session_id: str) -> List[str]:
    if not HAS_REDIS:
        return []
    r = await aioredis.from_url(settings.REDIS_URL)
    key = f"session:{session_id}:history"
    items = await r.lrange(key, 0, 9)
    return [i.decode("utf-8") if isinstance(i, (bytes, bytearray)) else i for i in items]
