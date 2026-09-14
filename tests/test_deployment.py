import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)


def test_health_check_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"


def test_readiness_probe_endpoint():
    res = client.get("/readiness")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"


def test_app_settings_configuration():
    assert settings.PORT == 8001
    assert settings.HOST == "0.0.0.0"
    assert "SEVERUS" in settings.APP_NAME
