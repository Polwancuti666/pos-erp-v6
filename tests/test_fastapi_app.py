from fastapi.testclient import TestClient
from pos_erp.fastapi_app import create_app


def test_fastapi_health_endpoint_returns_ok_and_version():
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "pos-erp-v6"


def test_fastapi_owner_dashboard_endpoint_returns_beauty_theme_metadata():
    client = TestClient(create_app())
    response = client.get("/dashboard/owner")
    assert response.status_code == 200
    data = response.json()
    assert data["theme"]["industry"] == "beauty-wellbeing"
    assert data["theme"]["mood"] == "cute-premium"


def test_fastapi_payment_provider_metadata_lists_bca_and_midtrans():
    client = TestClient(create_app())
    response = client.get("/payments/providers")
    assert response.status_code == 200
    assert response.json()["providers"] == ["BCA", "MIDTRANS"]
