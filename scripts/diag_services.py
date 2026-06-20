import asyncio
import os
from urllib.parse import urlparse

# Load .env
env = {}
with open('.env') as f:
    for line in f:
        line=line.strip()
        if not line or line.startswith('#'): continue
        if '=' in line:
            k,v=line.split('=',1)
            env[k.strip()]=v.strip()

POSTGRES_URL = env.get('POSTGRES_URL')
REDIS_URL = env.get('REDIS_URL')
QDRANT_URL = env.get('QDRANT_URL')
GROQ_API_KEY = env.get('GROQ_API_KEY')

print('ENV validation:')
if POSTGRES_URL and POSTGRES_URL.startswith('postgresql+asyncpg://'):
    if '?ssl' in POSTGRES_URL or 'sslmode' in POSTGRES_URL:
        print('❌ POSTGRES_URL contains ssl parameters — remove them and use connect_args')
    else:
        print('✅ POSTGRES_URL format OK')
else:
    print('❌ POSTGRES_URL missing or wrong prefix')

if REDIS_URL and REDIS_URL.startswith('redis://'):
    print('✅ REDIS_URL format OK')
else:
    print('❌ REDIS_URL missing or invalid')

if QDRANT_URL and QDRANT_URL.startswith('http://'):
    print('✅ QDRANT_URL format OK')
else:
    print('❌ QDRANT_URL missing or invalid')

if GROQ_API_KEY and not GROQ_API_KEY.lower().startswith('your_'):
    print('✅ GROQ_API_KEY present')
else:
    print('❌ GROQ_API_KEY missing or placeholder')


async def check_postgres():
    try:
        import asyncpg
        p = urlparse(POSTGRES_URL)
        user = p.username or 'postgres'
        password = p.password or ''
        host = p.hostname or 'localhost'
        port = p.port or 5432
        db = p.path.lstrip('/') or 'postgres'
        conn = await asyncpg.connect(host=host, port=port, user=user, password=password, database=db, ssl=False)
        await conn.close()
        print('✅ Postgres reachable')
    except Exception as e:
        print('❌ Postgres not reachable — reason:', e)

async def main():
    await check_postgres()
    # Redis
    try:
        import redis
        r = redis.from_url(REDIS_URL) if REDIS_URL else redis.Redis()
        r.ping()
        print('✅ Redis reachable')
    except Exception as e:
        print('❌ Redis not reachable — reason:', e)
    # Qdrant
    try:
        import requests
        url = QDRANT_URL.rstrip('/') + '/healthz'
        resp = requests.get(url, timeout=5)
        if resp.status_code in (200,204):
            print('✅ Qdrant reachable')
        else:
            print('❌ Qdrant not reachable — status', resp.status_code)
    except Exception as e:
        print('❌ Qdrant not reachable — reason:', e)

if __name__ == '__main__':
    asyncio.run(main())
