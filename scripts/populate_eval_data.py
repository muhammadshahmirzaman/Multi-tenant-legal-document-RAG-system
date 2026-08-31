import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import json
import uuid
from app.retrieval.qdrant_client import client as qdrant_client
from app.retrieval.bm25 import store as bm25_store
from app.workers.ingest_task import embed_texts, chunk_text


EVAL_TENANT = "eval-tenant"
GOLDEN_QA_PATH = Path(__file__).parent.parent / "evals" / "golden_qa.json"


def main():
    print(f"Loading golden QA from {GOLDEN_QA_PATH}")
    data = json.loads(GOLDEN_QA_PATH.read_text())

    docs = []
    for item in data:
        context = item.get("context", "")
        if not context:
            continue
        for i, chunk in enumerate(chunk_text(context)):
            docs.append({
                "id": str(uuid.uuid4()),
                "doc_id": f"golden_{item['id']}",
                "page": 1,
                "chunk_text": chunk,
                "tenant_id": EVAL_TENANT,
            })

    print(f"Created {len(docs)} chunks from {len(data)} QA items")

    texts = [d["chunk_text"] for d in docs]
    vectors = embed_texts(texts)

    pts = []
    for i, v in enumerate(vectors):
        pts.append({
            "id": docs[i]["id"],
            "vector": v,
            "payload": {
                "tenant_id": EVAL_TENANT,
                "doc_id": docs[i]["doc_id"],
                "page": docs[i]["page"],
                "chunk_text": docs[i]["chunk_text"],
            }
        })

    print("Upserting to Qdrant...")
    qdrant_client.upsert(pts)

    print("Building BM25 index...")
    bm25_store.build(EVAL_TENANT, docs)

    print(f"Successfully populated eval tenant: {EVAL_TENANT}")


if __name__ == "__main__":
    main()