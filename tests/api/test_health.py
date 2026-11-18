from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app_name"] == "AKiL Blog"
    assert data["environment"] == "development"


def test_docs_available(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200
