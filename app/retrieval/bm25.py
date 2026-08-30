from typing import Dict, List, Any
from rank_bm25 import BM25Okapi
import threading
import re


def tokenize(text: str):
    return re.findall(r"\w+", text.lower())


class BM25Store:
    def __init__(self):
        # tenant_id -> {"bm25": BM25Okapi, "docs": [payloads]}
        self.store: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()

    def build(self, tenant_id: str, docs: List[Dict[str, Any]]):
        # docs: list of {id, chunk_text, doc_id, page}
        with self.lock:
            corpus = [d.get("chunk_text", "") for d in docs]
            tokenized = [tokenize(c) for c in corpus]
            bm25 = BM25Okapi(tokenized)
            self.store[tenant_id] = {"bm25": bm25, "docs": docs}

    def search(self, tenant_id: str, query: str, top_n: int = 20) -> List[Dict[str, Any]]:
        with self.lock:
            entry = self.store.get(tenant_id)
            if not entry:
                return []
            tokenized = tokenize(query)
            scores = entry["bm25"].get_scores(tokenized)
            idxs = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_n]
            out = []
            for i in idxs:
                doc = entry["docs"][i]
                out.append({"id": doc.get("id"), "doc_id": doc.get("doc_id"), "page": doc.get("page"), "chunk_text": doc.get("chunk_text"), "score": float(scores[i])})
            return out

    def build_from_qdrant(self, tenant_id: str, qdrant_client, limit: int = 10000):
        """Build BM25 index by fetching documents from Qdrant for a tenant."""
        try:
            from qdrant_client.http.models import Filter, FieldCondition, MatchValue
            f = Filter(must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))])
            # Scroll through all points for this tenant
            docs = []
            offset = None
            while True:
                res = qdrant_client.client.scroll(
                    collection_name=qdrant_client.collection,
                    scroll_filter=f,
                    limit=min(100, limit - len(docs)) if limit else 100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )
                points, next_offset = res
                for point in points:
                    payload = point.payload
                    docs.append({
                        "id": str(point.id),
                        "doc_id": payload.get("doc_id"),
                        "page": payload.get("page"),
                        "chunk_text": payload.get("chunk_text", "")
                    })
                    if limit and len(docs) >= limit:
                        break
                if not next_offset or (limit and len(docs) >= limit):
                    break
                offset = next_offset
            
            if docs:
                self.build(tenant_id, docs)
                return len(docs)
        except Exception as e:
            print(f"Failed to build BM25 from Qdrant for tenant {tenant_id}: {e}")
        return 0


# Singleton
store = BM25Store()

# Provide class name used by nodes
BM25Store = BM25Store
