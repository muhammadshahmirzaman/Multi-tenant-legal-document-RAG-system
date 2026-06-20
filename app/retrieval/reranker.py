from typing import List, Dict, Any
from app.core.config import settings

try:
    from sentence_transformers import CrossEncoder
    HAS_CE = True
except Exception:
    CrossEncoder = None
    HAS_CE = False


def cohere_rerank(query: str, candidates: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
    # Rename kept for compatibility; use CrossEncoder if available
    if HAS_CE:
        try:
            model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            texts = [c.get("chunk_text", "") for c in candidates]
            pairs = [[query, t] for t in texts]
            scores = model.predict(pairs)
            ranked_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
            ordered = []
            for idx in ranked_idx:
                doc = candidates[idx]
                doc["rerank_score"] = float(scores[idx])
                ordered.append(doc)
            return ordered
        except Exception:
            pass
    # fallback: simple length-based heuristic
    ordered = sorted(candidates, key=lambda c: len(c.get("chunk_text", "")), reverse=True)[:top_k]
    for i, d in enumerate(ordered):
        d["rerank_score"] = float(i)
    return ordered
