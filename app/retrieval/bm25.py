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


# Singleton
store = BM25Store()

# Provide class name used by nodes
BM25Store = BM25Store
