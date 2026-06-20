from typing import Callable, List
from .state import AgentState
from . import nodes


class StateGraph:
    def __init__(self):
        # define edges in order
        self.pipeline: List[Callable[[AgentState], AgentState]] = [
            nodes.intent_classifier,
            nodes.query_planner,
            nodes.retriever,
            nodes.tool_dispatcher,
            nodes.generator,
            nodes.citation_grounder,
        ]

    async def run(self, state: AgentState) -> AgentState:
        s = state
        for fn in self.pipeline:
            s = await fn(s)
        return s


# Singleton
graph = StateGraph()
