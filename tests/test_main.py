from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_liveness():
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}

def test_readiness():
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}

def test_get_items():
    response = client.get("/api/v1/items")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 2

def test_get_item_found():
    response = client.get("/api/v1/items/1")
    assert response.status_code == 200
    assert response.json()["name"] == "Laptop"

def test_get_item_not_found():
    response = client.get("/api/v1/items/999")
    assert response.status_code == 404
