import asyncio
import httpx

async def test():
    async with httpx.AsyncClient(base_url='http://localhost:8000', timeout=60.0) as client:
        res = await client.post('/query/', headers={'x-api-key': 'demo-api-key-12345'}, json={'query': 'What are the indemnification obligations?', 'session_id': 'test-session-001'})
        print(res.status_code)
        print(res.text)

asyncio.run(test())
