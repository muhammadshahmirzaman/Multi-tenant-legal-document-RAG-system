import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient for synchronous tests."""
    return TestClient(app)


@pytest.fixture
def sample_tenant_headers():
    """Headers for dev tenant authentication."""
    return {"authorization": "Bearer tenant:dev-tenant"}


@pytest.fixture
def sample_query():
    """Sample query payload."""
    return {"query": "What is the warranty period?", "session_id": "test-session-001"}


@pytest.fixture
def sample_documents():
    """Sample documents for retrieval tests."""
    return [
        {"id": "1", "chunk_text": "This is a sample contract clause about warranty", "doc_id": "d1", "page": 1},
        {"id": "2", "chunk_text": "This clause discusses termination and liability", "doc_id": "d1", "page": 2},
    ]