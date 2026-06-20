from typing import List, cast
from .state import AgentState
from app.retrieval.bm25 import BM25Store
from app.retrieval.qdrant_client import QdrantClient
from app.agent.tools import clause_extractor, doc_compare, statute_lookup
from app.core.config import settings
import time

# Optional LLM: langchain_groq ChatGroq
try:
    from langchain_groq import ChatGroq
    HAS_GROQ = True
except Exception:
    ChatGroq = None
    HAS_GROQ = False


# Simple in-process singletons for retrievers
bm25_store = BM25Store()
qdrant_client = QdrantClient()


class _FallbackLLM:
    async def ainvoke(self, prompt: str):
        class R:
            def __init__(self, content):
                self.content = content
        # echo prompt truncated
        return R(content=f"[stub answer] {prompt[:500]}")


if HAS_GROQ and getattr(settings, 'GROQ_API_KEY', None):
    llm = ChatGroq(api_key=settings.GROQ_API_KEY, model=getattr(settings, 'LLM_MODEL', None), temperature=0)
else:
    llm = _FallbackLLM()


async def intent_classifier(state: AgentState) -> AgentState:
    q = state.get("query", "")
    ql = q.lower()
    if any(w in ql for w in ["compare", "difference", "vs"]):
        state["intent"] = "compare"
    elif any(w in ql for w in ["summary", "summarise", "summarize"]):
        state["intent"] = "summarise"
    elif any(w in ql for w in ["draft", "compose", "write"]):
        state["intent"] = "draft"
    else:
        state["intent"] = "lookup"
    return state


async def query_planner(state: AgentState) -> AgentState:
    q = state.get("query", "")
    if ";" in q or " and " in q:
        subs = [s.strip() for s in q.replace(" and ", ";").split(";") if s.strip()]
        state["sub_questions"] = subs
    else:
        state["sub_questions"] = [q]
    return state


async def retriever(state: AgentState) -> AgentState:
    subs: List[str] = state.get("sub_questions", [])
    retrieved = []
    start = time.time()
    for s in subs:
        bm25_hits = bm25_store.search(state.get("tenant_id", "default"), s, top_n=20)
        dense_hits = qdrant_client.search(s, tenant_id=state.get("tenant_id", "default"), top=20)
        combined = {h.get("id") or h.get("doc_id"): h for h in (bm25_hits + dense_hits) if h}
        hits = list(combined.values())[:5]
        retrieved.extend(hits)
    state["retrieved_chunks"] = retrieved
    state["retrieval_ms"] = int((time.time() - start) * 1000)
    return state


async def tool_dispatcher(state: AgentState) -> AgentState:
    intent = state.get("intent")
    tools = {}
    if intent == "compare":
        chunks = state.get("retrieved_chunks", [])
        if len(chunks) >= 2:
            a = chunks[0].get("chunk_text", "")
            b = chunks[1].get("chunk_text", "")
            tools["doc_compare"] = doc_compare(a, b)
    elif intent == "lookup":
        tools["statute_lookup"] = statute_lookup(state.get("query", ""))
    elif intent == "summarise":
        text = "\n\n".join([c.get("chunk_text", "") for c in state.get("retrieved_chunks", [])])
        tools["clauses"] = clause_extractor(text)
    state["tool_results"] = tools
    return state


async def generator(state: AgentState) -> AgentState:
    start = time.time()
    chunks = state.get("retrieved_chunks", [])[:5]
    chunks_text = "\n\n".join([f"[{c.get('doc_id')} p.{c.get('page',0)}] {c.get('chunk_text')}" for c in chunks])
    tools_text = "\n".join([f"{k}: {v}" for k, v in state.get("tool_results", {}).items()])
    prompt = f"Query: {state.get('query')}\n\nChunks:\n{chunks_text}\n\nTools:\n{tools_text}\n\nAnswer:"
    res = await llm.ainvoke(prompt)
    answer = getattr(res, 'content', str(res))
    state["answer"] = answer
    state["citations"] = [{"doc_id": c.get("doc_id"), "page": c.get("page"), "chunk_text": c.get("chunk_text")} for c in chunks]
    state["llm_ms"] = int((time.time() - start) * 1000)
    return state


async def citation_grounder(state: AgentState) -> AgentState:
    answers = []
    for _ in range(3):
        # run generator on a shallow copy of state
        tmp = cast(AgentState, dict(state))
        s = await generator(tmp)
        answers.append(s.get("answer", ""))
    consistent = sum(1 for a in answers if a == answers[0]) / max(len(answers), 1)
    state["hallucination_score"] = 1.0 - consistent
    return state
