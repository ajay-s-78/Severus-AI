import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.memory_service import memory_service

client = TestClient(app)


def test_correlation_id_and_security_headers():
    res = client.get("/health")
    assert res.status_code == 200
    assert "x-correlation-id" in res.headers
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("x-frame-options") == "DENY"
    assert res.headers.get("x-xss-protection") == "1; mode=block"


def test_custom_correlation_id_preservation():
    custom_id = "test-corr-id-12345"
    res = client.get("/health", headers={"X-Correlation-ID": custom_id})
    assert res.status_code == 200
    assert res.headers.get("x-correlation-id") == custom_id


def test_secret_filtering_audit_safeguard():
    fake_key = "AIzaSyABC12345678901234567890123456789"
    saved = memory_service.save_memory("secret_key", fake_key)
    assert saved is False
