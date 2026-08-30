from fastapi import Depends, Header, HTTPException
from jose import jwt, JWTError
from typing import Optional
from app.core.config import settings
from passlib.context import CryptContext
from redis import asyncio as aioredis
from app.db.session import AsyncSessionLocal
from sqlalchemy.future import select
from app.db.models import Tenant

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def _get_redis():
    try:
        return await aioredis.from_url(settings.REDIS_URL)
    except Exception:
        return None


async def get_current_tenant(authorization: Optional[str] = Header(None), x_api_key: Optional[str] = Header(None)) -> str:
    """Validate JWT RS256 or API key and return tenant_id.

    JWT: decode with settings.JWT_PUBLIC_KEY (PEM). Token must include tenant_id claim.
    API key: provided in X-API-KEY header; compare bcrypt hash against tenants table.
    Cache api key lookup in Redis key `apikey:{hash}` with TTL 300s.
    """
    # JWT flow
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
            if settings.JWT_PUBLIC_KEY:
                try:
                    payload = jwt.decode(token, settings.JWT_PUBLIC_KEY, algorithms=["RS256"])  # type: ignore
                    tenant_id = payload.get("tenant_id")
                    if tenant_id:
                        return tenant_id
                except JWTError:
                    raise HTTPException(status_code=401, detail="Invalid JWT token")
            # fallback dev format: tenant:<id>
            if token.startswith("tenant:"):
                return token.split(":", 1)[1]

    # API key flow
    if x_api_key:
        # Use Redis cache
        redis = await _get_redis()
        if redis:
            cache_key = f"apikey:{x_api_key}"
            cached = await redis.get(cache_key)
            if cached:
                return cached.decode("utf-8") if isinstance(cached, (bytes, bytearray)) else cached
        # Lookup in DB: find tenant where api_key_hash matches
        async with AsyncSessionLocal() as session:
            q = select(Tenant)
            res = await session.execute(q)
            rows = res.scalars().all()
            for t in rows:
                if t.api_key_hash and pwd_context.verify(x_api_key, t.api_key_hash):
                    tenant_id = str(t.id)
                    if redis:
                        await redis.set(cache_key, tenant_id, ex=300)
                    return tenant_id
        raise HTTPException(status_code=401, detail="Invalid API key")

    raise HTTPException(status_code=401, detail="Unauthorized")
