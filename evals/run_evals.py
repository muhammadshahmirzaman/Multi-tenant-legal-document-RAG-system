import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import json
from app.agent.graph import graph
from app.agent.state import AgentState
from app.retrieval.qdrant_client import client as qdrant_client
from app.retrieval.bm25 import store as bm25_store

EVAL_TENANT = "eval-tenant"


def score_faithfulness(generated: str, gold: str) -> float:
    ga = set(generated.lower().split())
    gb = set(gold.lower().split())
    if not gb:
        return 0.0
    return len(ga & gb) / len(gb)


def _ensure_eval_index():
    """Rebuild in-memory BM25 from Qdrant (populate runs in a separate process)."""
    count = bm25_store.build_from_qdrant(EVAL_TENANT, qdrant_client)
    if count == 0 and not qdrant_client.client:
        raise RuntimeError(
            "Qdrant is unavailable; run scripts/populate_eval_data.py after Qdrant is healthy."
        )
    print(f"Eval index ready for {EVAL_TENANT}: {count} BM25 docs from Qdrant")


async def run():
    _ensure_eval_index()
    p = Path(__file__).parent / "golden_qa.json"
    data = json.loads(p.read_text())
    scores = []
    for item in data:
        state: AgentState = {"query": item["query"], "tenant_id": EVAL_TENANT, "session_id": None}
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
