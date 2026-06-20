import json
import sys
from pathlib import Path
from app.agent.graph import graph
from app.agent.state import AgentState


def score_faithfulness(generated: str, gold: str) -> float:
    ga = set(generated.lower().split())
    gb = set(gold.lower().split())
    if not gb:
        return 0.0
    return len(ga & gb) / len(gb)


async def run():
    p = Path(__file__).parent / "golden_qa.json"
    data = json.loads(p.read_text())
    scores = []
    for item in data:
        state: AgentState = {"query": item["query"], "tenant_id": "eval-tenant", "session_id": None}
        final = await graph.run(state)
        gen = final.get("answer", "")
        s = score_faithfulness(gen, item.get("answer", "") + " " + item.get("context", ""))
        scores.append(s)
    avg = sum(scores) / len(scores) if scores else 0.0
    print(f"Average faithfulness: {avg:.3f}")
    if avg < 0.85:
        print("Faithfulness gate failed")
        sys.exit(2)
    print("Faithfulness gate passed")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
