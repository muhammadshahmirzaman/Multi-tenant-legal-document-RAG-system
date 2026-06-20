from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
import asyncio

try:
    import aioredis
    HAS_REDIS = True
except Exception:
    aioredis = None
    HAS_REDIS = False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token-bucket per-tenant rate limiter using Redis counters.

    Keys:
      plan:{tenant_id} -> hash with rpm and rpd
      rl:{tenant_key}:min -> counter expires in 60
      rl:{tenant_key}:day -> counter expires in 86400
    """

    def __init__(self, app):
        super().__init__(app)
        self.redis = None

    async def _ensure_redis(self):
        if not HAS_REDIS:
            return None
        if self.redis is None:
            self.redis = await aioredis.from_url(settings.REDIS_URL)
        return self.redis

    async def dispatch(self, request: Request, call_next):
        redis = await self._ensure_redis()
        tenant_key = request.headers.get("x-api-key") or request.headers.get("authorization") or "anonymous"
        # Default plan limits
        rpm = 60
        rpd = 1000
        if redis:
            try:
                plan_key = f"plan:{tenant_key}"
                plan = await redis.hgetall(plan_key)
                if plan:
                    # redis returns bytes; decode
                    if b"rpm" in plan:
                        rpm = int(plan[b"rpm"])
                    if b"rpd" in plan:
                        rpd = int(plan[b"rpd"])
            except Exception:
                pass

            min_key = f"rl:{tenant_key}:min"
            day_key = f"rl:{tenant_key}:day"
            try:
                # Use INCR and set expiry atomically
                cur_min = await redis.incr(min_key)
                if cur_min == 1:
                    await redis.expire(min_key, 60)
                cur_day = await redis.incr(day_key)
                if cur_day == 1:
                    await redis.expire(day_key, 86400)
                if int(cur_min) > rpm:
                    # compute retry-after from ttl
                    ttl = await redis.ttl(min_key)
                    raise HTTPException(status_code=429, detail="Rate limit exceeded", headers={"Retry-After": str(ttl)})
                if int(cur_day) > rpd:
                    ttl = await redis.ttl(day_key)
                    raise HTTPException(status_code=429, detail="Daily rate limit exceeded", headers={"Retry-After": str(ttl)})
            except HTTPException:
                raise
            except Exception:
                # On redis errors, allow
                pass

        response = await call_next(request)
        return response
