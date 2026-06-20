import asyncio
from app.agent.graph import graph
from app.agent.state import AgentState


def test_agent_simple_query():
    state: AgentState = {"query": "What is the warranty?", "tenant_id": "t1"}
    res = asyncio.run(graph.run(state))
    assert "answer" in res
