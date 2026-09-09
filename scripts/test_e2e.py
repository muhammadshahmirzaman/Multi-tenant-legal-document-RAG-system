#!/usr/bin/env python3
"""
Comprehensive End-to-End Test Suite and Evaluation Runner
Tests all system components and API endpoints directly without requiring pytest.
"""

import sys
import os
import io
import time
import json
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from app.main import app
from app.retrieval.bm25 import BM25Store
from app.cache.semantic_cache import make_hash

DEV_API_KEY_HEADER = {"X-API-Key": "demo-api-key-12345"}
DEV_BEARER_HEADER = {"Authorization": "Bearer tenant:dev-tenant"}

# Test Runner Tracker
test_results = []


def run_test(name, func):
    """Execute a test function and record the result."""
    print(f"\n[RUNNING] {name}...", flush=True)
    t0 = time.time()
    try:
        func()
        duration = time.time() - t0
        print(f"  --> [PASSED] {name} ({duration:.2f}s)", flush=True)
        test_results.append({"name": name, "status": "PASSED", "duration": duration, "error": None})
    except Exception as e:
        duration = time.time() - t0
        print(f"  --> [FAILED] {name} ({duration:.2f}s): {e}", flush=True)
        test_results.append({"name": name, "status": "FAILED", "duration": duration, "error": str(e)})


def main():
    print("=" * 70)
    print("Multi-Tenant Legal Document RAG - Full End-to-End Test & Evaluation")
    print("=" * 70)

    client = TestClient(app)

    # 1. Health Endpoint
    def test_health():
        res = client.get("/health/")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert data.get("status") == "ok", f"Expected status 'ok', got {data.get('status')}"
        assert "components" in data, "Missing 'components' key in health response"
        print(f"      Health components status: {data.get('components')}")

    run_test("GET /health/ Endpoint", test_health)

    # 2. Prometheus Metrics Endpoint
    def test_metrics():
        res = client.get("/metrics")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        assert any(m in res.text for m in ["http_requests", "process_cpu_seconds", "python_info"]), (
            "Prometheus metrics format missing expected metrics"
        )

    run_test("GET /metrics Endpoint", test_metrics)

    # 3. Ingestion Auth Validation
    def test_ingest_unauthorized():
        res = client.post("/ingest/")
        assert res.status_code == 401, f"Expected 401 Unauthorized, got {res.status_code}"

    run_test("POST /ingest/ Unauthorized Access Rejection", test_ingest_unauthorized)

    # 4. Ingestion & Status Workflow
    stored_task_id = None

    def test_ingest_and_status():
        nonlocal stored_task_id
        # Build minimal valid mock PDF byte stream
        pdf_bytes = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000052 00000 n \n0000000114 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
        files = {"file": ("master_service_agreement.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        res = client.post("/ingest/", files=files, headers=DEV_API_KEY_HEADER)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert "task_id" in data, "Response missing task_id"
        assert data.get("status") == "queued", f"Expected queued, got {data.get('status')}"
        stored_task_id = data["task_id"]

        # Check status endpoint
        status_res = client.get(f"/ingest/status/{stored_task_id}")
        assert status_res.status_code == 200, f"Expected 200, got {status_res.status_code}: {status_res.text}"
        status_data = status_res.json()
        assert status_data.get("task_id") == stored_task_id
        assert "status" in status_data

    run_test("POST /ingest/ & GET /ingest/status/{task_id}", test_ingest_and_status)

    # 5. Query Auth Validation
    def test_query_unauthorized():
        res = client.post("/query/", json={"query": "Who is liable for breach of warranty?"})
        assert res.status_code == 401, f"Expected 401, got {res.status_code}"

    run_test("POST /query/ Unauthorized Access Rejection", test_query_unauthorized)

    # 6. Query Execution with Bearer Token
    def test_query_bearer_auth():
        payload = {"query": "What are the indemnification obligations in the contract?"}
        res = client.post("/query/", json=payload, headers=DEV_BEARER_HEADER)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert "answer" in data, "Missing answer in response"
        assert "citations" in data, "Missing citations list"
        assert "hallucination_score" in data, "Missing hallucination_score"
        assert "metrics" in data, "Missing latency metrics"
        print(f"      Response preview: {data['answer'][:120]}...")
        print(f"      Hallucination score: {data['hallucination_score']}")
        print(f"      Execution metrics: {data['metrics']}")

    run_test("POST /query/ End-to-End RAG (Bearer Auth)", test_query_bearer_auth)

    # 7. Query Execution with API Key and Session Multi-Turn History
    def test_query_api_key_with_session():
        sess_id = f"test-sess-{int(time.time())}"
        # Turn 1
        res1 = client.post(
            "/query/",
            json={"query": "Explain the governing law of the contract.", "session_id": sess_id},
            headers=DEV_API_KEY_HEADER,
        )
        assert res1.status_code == 200, f"Expected 200, got {res1.status_code}: {res1.text}"
        data1 = res1.json()
        assert data1.get("answer"), "Turn 1 missing answer"

        # Turn 2
        res2 = client.post(
            "/query/",
            json={"query": "What are the termination conditions?", "session_id": sess_id},
            headers=DEV_API_KEY_HEADER,
        )
        assert res2.status_code == 200, f"Expected 200, got {res2.status_code}: {res2.text}"
        data2 = res2.json()
        assert data2.get("answer"), "Turn 2 missing answer"

    run_test("POST /query/ Multi-Turn Session with API Key", test_query_api_key_with_session)

    # 8. Server-Sent Events (SSE) Streaming Endpoint
    def test_query_stream():
        params = {"query": "Summarize key warranties and representations"}
        res = client.get("/query/stream", params=params, headers=DEV_API_KEY_HEADER)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        assert "text/event-stream" in res.headers.get("content-type", "")
        content = res.text
        assert "event: step" in content or "event: done" in content, (
            f"Expected SSE events in stream output. Got: {content[:200]}"
        )
        print(f"      SSE Stream received {len(content)} bytes of events")

    run_test("GET /query/stream Real-Time Agent Steps Streaming", test_query_stream)

    # 9. In-Memory Retrieval & BM25 Unit Evaluation
    def test_retrieval_bm25():
        store = BM25Store()
        docs = [
            {"id": "c1", "chunk_text": "The Supplier agrees to indemnify the Customer against all patent claims.", "doc_id": "doc1", "page": 1},
            {"id": "c2", "chunk_text": "Either party may terminate this agreement with 30 days written notice.", "doc_id": "doc1", "page": 2},
            {"id": "c3", "chunk_text": "Governing law shall be the laws of the State of Delaware.", "doc_id": "doc2", "page": 1},
        ]
        store.build("tenant-e2e", docs)
        results = store.search("tenant-e2e", "indemnify patent", top_n=2)
        assert len(results) >= 1, "BM25 search should return at least 1 match"
        assert results[0]["id"] == "c1", f"Expected top match c1, got {results[0]['id']}"

    run_test("Retrieval Engine: BM25 Multi-Tenant Indexing & Search", test_retrieval_bm25)

    # 10. Semantic Cache Hashing
    def test_semantic_cache_hash():
        import asyncio
        h1 = asyncio.run(make_hash("What is the dispute resolution clause?"))
        h2 = asyncio.run(make_hash("What is the dispute resolution clause?"))
        h3 = asyncio.run(make_hash("Different query text"))
        assert len(h1) == 64, "SHA-256 hash must be 64 hex characters"
        assert h1 == h2, "Identical queries must produce identical hashes"
        assert h1 != h3, "Different queries must produce distinct hashes"

    run_test("Cache Subsystem: Deterministic SHA-256 Hashing", test_semantic_cache_hash)

    # Summary Report
    print("\n" + "=" * 70)
    print("SUMMARY OF END-TO-END TEST RESULTS")
    print("=" * 70)
    passed_count = sum(1 for t in test_results if t["status"] == "PASSED")
    failed_count = sum(1 for t in test_results if t["status"] == "FAILED")
    total_count = len(test_results)

    for r in test_results:
        status_marker = "[OK]" if r["status"] == "PASSED" else "[FAIL]"
        err_msg = f" - Error: {r['error']}" if r["error"] else ""
        print(f"{status_marker} {r['name']:<55} {r['duration']:>6.2f}s{err_msg}")

    print("-" * 70)
    print(f"Total Tests: {total_count} | Passed: {passed_count} | Failed: {failed_count}")
    print("=" * 70)

    if failed_count > 0:
        print("\n[RESULT] Some tests failed. Please review errors above.")
        sys.exit(1)
    else:
        print("\n[RESULT] ALL END-TO-END TESTS PASSED SUCCESSFULLY! 100% SUCCESS.")
        sys.exit(0)


if __name__ == "__main__":
    main()
