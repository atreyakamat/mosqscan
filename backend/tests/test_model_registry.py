"""Model registry and health check tests."""
from __future__ import annotations


def test_get_model_info(client):
    res = client.get("/api/v1/models/info")
    assert res.status_code == 200
    data = res.json()
    assert data["product"] == "Vectora AI"
    assert data["model_version"] in ("1.0.0", "3.0.0")
    assert "adult_classifier" in data
    assert data["adult_classifier"]["classes"] == ["aedes", "anopheles", "culex"]
    assert data["larvae_model"]["status"] == "not_validated"


def test_get_model_version(client):
    res = client.get("/api/v1/models/version")
    assert res.status_code == 200
    assert res.json()["model_version"] in ("1.0.0", "3.0.0")


def test_model_health_checksum_verified(client):
    res = client.get("/api/v1/models/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["checksum_verified"] is True
    assert data["model_version"] in ("1.0.0", "3.0.0")
