from typing import List, Dict, Any
from app.core.config import settings

try:
    from qdrant_client import QdrantClient as _Qdrant
    from qdrant_client.http.models import VectorParams, Filter, FieldCondition, MatchValue
    HAS_QDRANT = True
except Exception:
    _Qdrant = None
    HAS_QDRANT = False


class QdrantClient:
    def __init__(self):
        self.client = None
        self.collection = "legal_docs"
        if HAS_QDRANT:
            try:
                self.client = _Qdrant(url=settings.QDRANT_URL)
                # ensure collection exists with vector size 384
                try:
                    self.client.get_collection(self.collection)
                except Exception:
                    self.client.recreate_collection(collection_name=self.collection, vectors=VectorParams(size=384, distance="Cosine"))
            except Exception:
                self.client = None

    def upsert(self, vectors: List[Dict[str, Any]]):
        """Upsert a list of {id, vector, payload} into Qdrant."""
        if not self.client:
            # fallback: store nothing
            return False
        points = []
        for v in vectors:
            points.append({"id": v["id"], "vector": v["vector"], "payload": v.get("payload", {})})
        self.client.upsert(collection_name=self.collection, points=points)
        return True

    def search(self, query: str, tenant_id: str = "default", top: int = 5) -> List[Dict[str, Any]]:
        if not self.client:
            # fallback: return empty
            return []
        # naive text embed via local model not implemented here; assume query vector created elsewhere
        from qdrant_client.http.models import Filter, FieldCondition, MatchValue
        f = Filter(must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))])
        try:
            res = self.client.search(collection_name=self.collection, query_vector=[0.0]*384, limit=top, filter=f)
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
