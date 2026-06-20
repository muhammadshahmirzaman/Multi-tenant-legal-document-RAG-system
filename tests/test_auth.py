import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_jwt_dev_tenant_header():
    headers = {"authorization": "Bearer tenant:dev-tenant"}
    res = client.post("/query/", json={"query": "hello"}, headers=headers)
    assert res.status_code == 200
    assert "answer" in res.json()
