import asyncio
from app.cache.semantic_cache import make_hash, get_cached, set_cached


def test_hash():
    h = asyncio.run(make_hash("hello"))
    assert len(h) == 64

# Redis-dependent tests are skipped if redis not available
