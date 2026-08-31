import os
from typing import List, Dict, Any
from app.core.config import settings

try:
    from qdrant_client import QdrantClient as _Qdrant
    from qdrant_client.http.models import VectorParams, Distance, Filter, FieldCondition, MatchValue
    HAS_QDRANT = True
except Exception:
    _Qdrant = None
    HAS_QDRANT = False

try:
    from sentence_transformers import SentenceTransformer
    EMBED_MODEL = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))
    HAS_SBT = True
except Exception:
    EMBED_MODEL = None
    HAS_SBT = False


class QdrantClient:
    def __init__(self):
        self.client = None
        self.collection = "legal_docs"
        self._initialized = False

    def _ensure_initialized(self):
        if self._initialized:
            return
        if HAS_QDRANT:
            try:
                self.client = _Qdrant(url=settings.QDRANT_URL)
                try:
                    self.client.get_collection(self.collection)
                except Exception:
                    self.client.create_collection(
                        collection_name=self.collection,
                        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                    )
            except Exception as e:
                print(f"Qdrant client initialization failed: {e}")
                self.client = None
        self._initialized = True

    def _embed_query(self, query: str) -> List[float]:
        if HAS_SBT and EMBED_MODEL is not None:
            return EMBED_MODEL.encode(query).tolist()
        return [0.0] * 384

    def upsert(self, vectors: List[Dict[str, Any]]):
        """Upsert a list of {id, vector, payload} into Qdrant."""
        self._ensure_initialized()
        if not self.client:
            return False
        points = []
        for v in vectors:
            points.append({"id": v["id"], "vector": v["vector"], "payload": v.get("payload", {})})
        self.client.upsert(collection_name=self.collection, points=points)
        return True

    def search(self, query: str, tenant_id: str = "default", top: int = 5) -> List[Dict[str, Any]]:
        self._ensure_initialized()
        if not self.client:
            return []
        from qdrant_client.http.models import Filter, FieldCondition, MatchValue
        f = Filter(must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))])
        try:
            query_vector = self._embed_query(query)
            res = self.client.search(collection_name=self.collection, query_vector=query_vector, limit=top, filter=f)
            out = []
            for hit in res:
                payload = hit.payload
                out.append({
                    "id": str(hit.id),
                    "doc_id": payload.get("doc_id"),
                    "page": payload.get("page"),
                    "chunk_text": payload.get("chunk_text"),
                    "score": hit.score,
                })
            return out
        except Exception:
            return []


# singleton
client = QdrantClient()
