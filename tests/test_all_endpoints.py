import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

DEV_HEADER = {"X-API-Key": "demo-api-key-12345"}


def test_health_endpoint():
    res = client.get("/health/")
    assert res.status_code == 200
    data = res.json()
    assert data.get("status") == "ok"
    assert "components" in data


def test_metrics_endpoint():
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "http_requests" in res.text or "process_cpu_seconds" in res.text or "python_info" in res.text


def test_ingest_endpoint_unauthorized():
    res = client.post("/ingest/")
    assert res.status_code == 401


def test_ingest_and_status_endpoint():
    dummy_pdf_content = b"%PDF-1.4 %DUMMY PDF CONTENT FOR TESTING INGESTION"
    files = {"file": ("test_doc.pdf", io.BytesIO(dummy_pdf_content), "application/pdf")}
    res = client.post("/ingest/", files=files, headers=DEV_HEADER)
    assert res.status_code == 200
    data = res.json()
    assert "task_id" in data
    assert data.get("status") == "queued"

    task_id = data["task_id"]
    status_res = client.get(f"/ingest/status/{task_id}")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data.get("task_id") == task_id
    assert "status" in status_data


def test_query_endpoint_unauthorized():
    res = client.post("/query/", json={"query": "Test query"})
    assert res.status_code == 401


def test_query_endpoint_success():
    payload = {"query": "What are the indemnification obligations?", "session_id": "test-sess-1"}
    res = client.post("/query/", json=payload, headers=DEV_HEADER)
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert "citations" in data
    assert "hallucination_score" in data
    assert "metrics" in data


def test_query_stream_endpoint():
    res = client.get("/query/stream", params={"query": "Summarize warranty terms", "session_id": "test-sess-1"}, headers=DEV_HEADER)
    assert res.status_code == 200
    assert "text/event-stream" in res.headers.get("content-type", "")
    assert len(res.text) > 0
