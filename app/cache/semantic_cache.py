import hashlib
import json
from typing import Any, Optional
from app.core.config import settings

try:
    import aioredis
    HAS_REDIS = True
except Exception:
    aioredis = None
    HAS_REDIS = False


async def make_hash(text: str) -> str:
    h = hashlib.sha256()
    h.update(text.encode("utf-8"))
    return h.hexdigest()


async def get_cached(tenant_id: str, text: str) -> Optional[Any]:
    if not HAS_REDIS:
        return None
    key = f"cache:{tenant_id}:{await make_hash(text)}"
    r = await aioredis.from_url(settings.REDIS_URL)
    val = await r.get(key)
    if not val:
        return None
    try:
        return json.loads(val)
    except Exception:
        return None


async def set_cached(tenant_id: str, text: str, value: Any, ttl: int = 3600):
    if not HAS_REDIS:
        return False
    key = f"cache:{tenant_id}:{await make_hash(text)}"
    r = await aioredis.from_url(settings.REDIS_URL)
    await r.set(key, json.dumps(value), ex=ttl)
    return True


async def flush_tenant_cache(tenant_id: str):
    if not HAS_REDIS:
        return 0
    r = await aioredis.from_url(settings.REDIS_URL)
    cursor = b"0"
    deleted = 0
    pattern = f"cache:{tenant_id}:*"
    async for key in r.scan_iter(match=pattern):
        await r.delete(key)
        deleted += 1
    return deleted
