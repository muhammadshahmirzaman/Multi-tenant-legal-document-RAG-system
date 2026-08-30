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

## Query Processing Architecture

The following diagram illustrates the complete process from the moment a user submits a prompt (`POST /query/`) to the moment the system returns a response. It details the authentication, history retrieval, and the internal agent graph node execution, along with the specific files responsible for each step.

```mermaid
flowchart TD
    %% Styling
    classDef client fill:#e1f5fe,stroke:#0288d1,stroke-width:2px,color:#01579b
    classDef auth fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#e65100
    classDef state fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#4a148c
    classDef agent fill:#e8f5e9,stroke:#388e3c,stroke-width:2px,color:#1b5e20
    classDef external fill:#ffebee,stroke:#d32f2f,stroke-width:2px,color:#b71c1c
    classDef response fill:#e0f2f1,stroke:#00796b,stroke-width:2px,color:#004d40

    %% Client Layer
    Start([Client Request]):::client
    Prompt[POST /query/ \n Payload: query, session_id\n<br><i>app/api/query.py</i>]:::client

    %% Authentication Layer
    Auth{Authentication \n `get_current_tenant`\n<br><i>app/core/auth.py</i>}:::auth
    RedisCache[(Redis API Key Cache)]:::external
    DB[(PostgreSQL Tenant DB)]:::external
    AuthFail[401 Unauthorized]:::response

    %% State & History Layer
    CheckSession{Session ID \n provided?}:::state
    GetHistory[(Fetch History from Redis\n`get_history`)\n<br><i>app/cache/session.py</i>]:::external
    InitState[Initialize AgentState \n query, tenant_id, session_id, history\n<br><i>app/api/query.py</i>]:::state

    %% Agent Graph Layer (Nodes)
    subgraph AgentGraph [Agent Execution Graph - <i>app/agent/nodes.py & graph.py</i>]
        Node1[1. Intent Classifier\nDetermines: compare, summarise, draft, or lookup\n<br><i>app/agent/nodes.py</i>]:::agent
        Node2[2. Query Planner\nSplits query into sub-questions\n<br><i>app/agent/nodes.py</i>]:::agent
        
        subgraph Retriever [3. Retriever Node - <i>app/agent/nodes.py</i>]
            BM25[(BM25 Store\n<br><i>app/retrieval/bm25.py</i>)]:::external
            Qdrant[(Qdrant Vector DB\n<br><i>app/retrieval/qdrant_client.py</i>)]:::external
            Node3[Execute Searches per sub-question \n Merge & Deduplicate Top 5]:::agent
        end
        
        Node4[4. Tool Dispatcher\nDispatches specific tools based on intent\n<br><i>app/agent/nodes.py</i> & <i>app/agent/tools.py</i>]:::agent
        Node5[5. Generator\nBuilds prompt with chunks & tool results\nCalls LLM\n<br><i>app/agent/nodes.py</i>]:::agent
        LLM((Groq LLM)):::external
        Node6[6. Citation Grounder\nRuns generator 3x to calculate hallucination score\n<br><i>app/agent/nodes.py</i>]:::agent
    end

    %% Post-Graph Layer
    SaveHistory[(Save Answer to Session Cache\n`push_message`\n<br><i>app/cache/session.py</i>)]:::external
    Response[Return JSON Response \n answer, citations, metrics, score\n<br><i>app/api/query.py</i>]:::response

    %% Flow logic
    Start --> Prompt
    Prompt --> Auth
    Auth -- API Key / JWT Valid --> CheckSession
    Auth -- Invalid --> AuthFail
    
    Auth -.- RedisCache
    Auth -.- DB
    
    CheckSession -- Yes --> GetHistory --> InitState
    CheckSession -- No --> InitState
    
    InitState --> Node1
    Node1 --> Node2
    Node2 --> Node3
    
    Node3 -.- BM25
    Node3 -.- Qdrant
    
    Node3 --> Node4
    Node4 --> Node5
    
    Node5 -.- LLM
    Node5 --> Node6
    Node6 --> SaveHistory
    SaveHistory --> Response
```
