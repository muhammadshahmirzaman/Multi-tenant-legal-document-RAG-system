from app.retrieval.bm25 import BM25Store


def test_bm25_build_search():
    store = BM25Store()
    docs = [{"id": "1", "chunk_text": "This is a sample contract clause about warranty", "doc_id": "d1", "page": 1},
            {"id": "2", "chunk_text": "This clause discusses termination and liability", "doc_id": "d1", "page": 2}]
    store.build("t1", docs)
    res = store.search("t1", "warranty", top_n=2)
    assert len(res) >= 1
