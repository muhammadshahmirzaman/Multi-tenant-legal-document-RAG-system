import os
import uuid
import math
import time
from typing import List
from app.workers.celery_app import celery
from app.retrieval.qdrant_client import client as qdrant_client
from app.db.session import AsyncSessionLocal
from app.db.models import Document
from app.cache.semantic_cache import flush_tenant_cache

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    from sentence_transformers import SentenceTransformer
    EMBED_MODEL = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))
    HAS_SBT = True
except Exception:
    EMBED_MODEL = None
    HAS_SBT = False


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    tokens = text.split()
    chunks = []
    i = 0
    while i < len(tokens):
        chunk = tokens[i:i+chunk_size]
        chunks.append(" ".join(chunk))
        i += chunk_size - overlap
    return chunks


def embed_texts(texts: List[str]) -> List[List[float]]:
    if HAS_SBT and EMBED_MODEL is not None:
        vectors = EMBED_MODEL.encode(texts, convert_to_numpy=False)
        # ensure lists
        return [list(v) for v in vectors]
    # fallback zero vectors of size 384
    return [[0.0]*384 for _ in texts]


@celery.task(name="ingest_pdf")
def ingest_pdf(file_path: str, tenant_id: str, filename: str):
    start = time.time()
    if not fitz:
        return {"status": "error", "reason": "pymupdf not installed"}
    doc = fitz.open(file_path)
    page_texts = []
    for p in range(doc.page_count):
        page = doc.load_page(p)
        text = page.get_text()
        page_texts.append((p+1, text))
    # chunk
    chunks = []
    for page_num, text in page_texts:
        for c in chunk_text(text):
            chunks.append({"doc_id": str(uuid.uuid4()), "page": page_num, "chunk_text": c, "filename": filename, "tenant_id": tenant_id})
    texts = [c["chunk_text"] for c in chunks]
    vectors = embed_texts(texts)
    # prepare upsert payload
    pts = []
    for i, v in enumerate(vectors):
        pts.append({"id": chunks[i]["doc_id"], "vector": v, "payload": {"tenant_id": tenant_id, "doc_id": chunks[i]["doc_id"], "page": chunks[i]["page"], "chunk_index": i, "chunk_text": chunks[i]["chunk_text"], "filename": filename}})
    upserted = qdrant_client.upsert(pts)
    # insert document record
    async def _insert_doc():
        async with AsyncSessionLocal() as session:
            doc_record = Document(tenant_id=tenant_id, filename=filename, page_count=doc.page_count, chunk_count=len(chunks))
            session.add(doc_record)
            await session.commit()
    try:
        import asyncio
        asyncio.run(_insert_doc())
    except Exception:
        pass
    # flush cache
    try:
        import asyncio
        asyncio.run(flush_tenant_cache(tenant_id))
    except Exception:
        pass
    return {"status": "success", "chunks": len(chunks), "upserted": bool(upserted), "duration_s": time.time()-start}


def ingest_text(file_path: str, tenant_id: str, filename: str):
    """Synchronous ingestion for plain text files (used by scripts/tools).
    Mirrors the logic in `ingest_pdf` but reads text from a file instead of PDF pages.
    """
    start = time.time()
    # read file
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return {"status": "error", "reason": "could not read file"}

    # chunk
    chunks = []
    for i, c in enumerate(chunk_text(text)):
        chunks.append({"doc_id": str(uuid.uuid4()), "page": 1, "chunk_text": c, "filename": filename, "tenant_id": tenant_id})

    texts = [c["chunk_text"] for c in chunks]
    vectors = embed_texts(texts)

    pts = []
    for i, v in enumerate(vectors):
        pts.append({
            "id": chunks[i]["doc_id"],
            "vector": v,
            "payload": {"tenant_id": tenant_id, "doc_id": chunks[i]["doc_id"], "page": chunks[i]["page"], "chunk_index": i, "chunk_text": chunks[i]["chunk_text"], "filename": filename}
        })

    upserted = qdrant_client.upsert(pts)

    # insert document record
    async def _insert_doc():
        async with AsyncSessionLocal() as session:
            doc_record = Document(tenant_id=tenant_id, filename=filename, page_count=1, chunk_count=len(chunks))
            session.add(doc_record)
            await session.commit()
    try:
        import asyncio
        asyncio.run(_insert_doc())
    except Exception:
        pass

    # flush cache
    try:
        import asyncio
        asyncio.run(flush_tenant_cache(tenant_id))
    except Exception:
        pass

    return {"status": "success", "chunks": len(chunks), "upserted": bool(upserted), "duration_s": time.time()-start}
