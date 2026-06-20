from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from app.core.auth import get_current_tenant
from app.agent import graph
from app.agent.state import AgentState
from app.cache.session import push_message, get_history
import asyncio
import time

router = APIRouter(prefix="/query")

class QueryRequest(BaseModel):
    query: str
    session_id: str | None = None


@router.post("/")
async def query(req: QueryRequest, tenant_id: str = Depends(get_current_tenant)):
    state: AgentState = {
        "query": req.query,
        "tenant_id": tenant_id,
        "session_id": req.session_id,
    }
    start = time.time()
    # inject history
    if req.session_id:
        hist = await get_history(req.session_id)
        if hist:
            state["history"] = hist
    final = await graph.graph.run(state)
    # push last answer to session
    if req.session_id:
        await push_message(req.session_id, final.get("answer", ""))
    duration = time.time() - start
    return JSONResponse({"answer": final.get("answer"), "citations": final.get("citations", []), "hallucination_score": final.get("hallucination_score", 0.0), "metrics": {"retrieval_ms": final.get("retrieval_ms"), "llm_ms": final.get("llm_ms"), "duration_s": duration}})


@router.get("/stream")
async def stream(request: Request, query: str, session_id: str | None = None, tenant_id: str = Depends(get_current_tenant)):
    async def event_generator():
        state: AgentState = {"query": query, "tenant_id": tenant_id, "session_id": session_id}
        # Run nodes step by step and yield events after each
        from app.agent import nodes
        steps = [nodes.intent_classifier, nodes.query_planner, nodes.retriever, nodes.tool_dispatcher, nodes.generator, nodes.citation_grounder]
        for fn in steps:
            if await request.is_disconnected():
                break
            s_before = {k: state.get(k) for k in ("intent", "sub_questions", "retrieved_chunks", "tool_results", "answer")}
            state = await fn(state)
            s_after = {k: state.get(k) for k in ("intent", "sub_questions", "retrieved_chunks", "tool_results", "answer")}
            yield {"type": "step", "content": {"node": fn.__name__, "before": s_before, "after": s_after}}
            await asyncio.sleep(0.01)
        yield {"type": "done", "content": {"answer": state.get("answer"), "citations": state.get("citations"), "hallucination_score": state.get("hallucination_score")}}
    return EventSourceResponse(event_generator())
