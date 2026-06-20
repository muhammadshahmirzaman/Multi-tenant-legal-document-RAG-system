from typing import TypedDict, List, Dict, Any, Optional


class AgentState(TypedDict, total=False):
    query: str
    tenant_id: str
    session_id: Optional[str]
    intent: Optional[str]
    sub_questions: List[str]
    retrieved_chunks: List[Dict[str, Any]]
    tool_results: Dict[str, Any]
    answer: Optional[str]
    citations: List[Dict[str, Any]]
    hallucination_score: float
    # internal timings/metrics
    retrieval_ms: Optional[int]
    llm_ms: Optional[int]
    cache_hit: Optional[bool]
