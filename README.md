# Multi-tenant-legal-document-RAG-system
Production-grade multi-tenant legal document RAG platform featuring a LangGraph ReAct agent loop, hybrid search (Qdrant + BM25), local Cross-Encoder reranking, SelfCheckGPT grounding, and a Redis-backed semantic cache. Fully containerized with FastAPI, Postgres, and Celery workers.

### Quick Start

    # Step 1 — generate JWT keys (run once)
    openssl genrsa -out private.pem 2048
    openssl rsa -in private.pem -pubout -out public.pem

    # Step 2 — install dependencies
    pip install -r requirements.txt

    # Step 3 — run DB migrations
    alembic upgrade head

    # Step 4 — seed demo tenant
    python -m scripts.seed_tenant

    # Step 5 — load CUAD dataset (terminal 1)
    python -m scripts.load_dataset

    # Step 6 — start Celery worker (terminal 2)
    celery -A app.workers.celery_app worker --loglevel=info --pool=solo

    # Step 7 — start FastAPI (terminal 3)
    uvicorn app.main:app --reload --port 8000

    # Step 8 — test first query
    curl -X POST http://localhost:8000/query \
      -H "X-API-Key: demo-api-key-12345" \
      -H "Content-Type: application/json" \
      -d '{
        "query": "What are the indemnification obligations?",
        "session_id": "test-session-001"
      }'
