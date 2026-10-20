"""Tests for the /health endpoint."""

from fastapi.testclient import TestClient

from app.main import app, get_settings

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "Nirikkha"
    assert set(body["providers_configured"]) == {"groq", "gemini", "neo4j", "supabase"}


def test_health_never_leaks_secrets():
    text = client.get("/health").text
    s = get_settings()
    for secret in (s.groq_api_key, s.gemini_api_key):
        if secret:
            assert secret not in text


def test_head_requests_supported():
    # Uptime pingers and the host's port probe use HEAD.
    assert client.head("/").status_code == 200
    assert client.head("/health").status_code == 200