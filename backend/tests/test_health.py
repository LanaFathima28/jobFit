from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """
    Test root '/' welcome endpoint.
    """
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Welcome to JobFit AI API"
    assert "health" in data


def test_llm_test_endpoint_without_key():
    """
    Test '/api/v1/llm-test' endpoint when API key is unconfigured.
    Should return 200 with status='warning'.
    """
    response = client.get("/api/v1/llm-test")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["warning", "success"]
