import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_empty_search():
    response = client.get("/api/search?q=")
    assert response.status_code == 200
    data = response.json()
    # With empty query, no semantic parsing happens, so results should match all context filters if provided
    # or just return all items if no context. Let's assume it returns all.
    assert isinstance(data["results"], list)

def test_search_needs_refinement():
    # A generic query that should trigger needs_refinement
    response = client.get("/api/search?q=random_gibberish_123")
    assert response.status_code == 200
    data = response.json()
    assert data["needs_refinement"] is True
    assert isinstance(data["suggestions"], list)

def test_search_with_context():
    # Simulate a user clicking the "Goa" suggestion chip
    response = client.get("/api/search?q=&context=Goa")
    assert response.status_code == 200
    data = response.json()
    
    # Verify all results contain Goa in their metadata
    for result in data["results"]:
        meta = str(result["metadata"]).lower()
        assert "goa" in meta
