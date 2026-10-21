"""Tests for Nirikkha Private Mode (local Ollama models, fail-closed isolation)."""

import json
from datetime import date
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.routes import PRIVATE_UNAVAILABLE, execute, get_inline, get_runner, get_store
from app.auth.deps import get_optional_user
from app.llm.client import LLMClient, PrivateModeUnavailable
from app.main import app

MSG = [{"role": "system", "content": "Return json."}, {"role": "user", "content": "analyze"}]


def ollama_chat_ok(content: str = '{"ok": true}'):
    return httpx.Response(
        200,
        json={
            "message": {"content": content},
            "prompt_eval_count": 12,
            "eval_count": 8,
        },
    )


def test_private_mode_routes_to_ollama_only_and_logs_zero_cost(tmp_path):
    recorded_urls = []

    def handler(request: httpx.Request):
        recorded_urls.append(str(request.url))
        if "api/chat" in str(request.url):
            body = json.loads(request.read())
            assert body["model"] == "qwen2.5:1.5b"
            assert body["stream"] is False
            return ollama_chat_ok('{"status": "clean"}')
        return httpx.Response(500, text="Should not be called")

    client = LLMClient(
        groq_key="mock-groq",
        gemini_key="mock-gemini",
        ollama_url="http://localhost:11434",
        ollama_model_fast="qwen2.5:1.5b",
        ollama_model_general="gemma3:1b",
        cache_dir=tmp_path / "cache",
        usage_log=tmp_path / "usage.jsonl",
        transport=httpx.MockTransport(handler),
    )

    result = client.complete("fast", MSG, json_mode=True, private=True)

    assert result.provider == "ollama"
    assert result.model == "qwen2.5:1.5b"
    assert result.data == {"status": "clean"}
    assert result.cost_usd == 0.0
    assert len(recorded_urls) == 1
    assert "localhost:11434" in recorded_urls[0]
    assert not any("groq" in url or "googleapis" in url for url in recorded_urls)

    log_lines = (tmp_path / "usage.jsonl").read_text().splitlines()
    assert len(log_lines) == 1
    log_row = json.loads(log_lines[0])
    assert log_row["provider"] == "ollama"
    assert log_row["cost_usd"] == 0.0


def test_private_mode_fails_closed_when_ollama_unreachable():
    called = []

    def handler(request: httpx.Request):
        called.append(str(request.url))
        if "localhost" in str(request.url):
            raise httpx.ConnectError("Connection refused")
        return httpx.Response(200, json={"text": "from groq"})

    client = LLMClient(
        groq_key="mock-groq",
        gemini_key="mock-gemini",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(PrivateModeUnavailable) as exc:
        client.complete("fast", MSG, private=True)

    assert "Private mode needs the local model runtime (Ollama)" in str(exc.value)
    # Crucial: verify Groq and Gemini were NEVER called
    assert not any("groq" in url or "googleapis" in url for url in called)


def test_private_mode_json_retries_once():
    attempts = []

    def handler(request: httpx.Request):
        attempts.append(request)
        if len(attempts) == 1:
            return ollama_chat_ok("not json here")
        return ollama_chat_ok('{"retry": "success"}')

    client = LLMClient(
        transport=httpx.MockTransport(handler),
    )

    result = client.complete("fast", MSG, json_mode=True, private=True)
    assert result.data == {"retry": "success"}
    assert len(attempts) == 2


class MockStore:
    def __init__(self):
        self.rows = {}

    def busy(self):
        return False

    def find_done(self, cik, as_of, key, private=False):
        return None

    def create(self, cik, as_of, decision, key, source="live", user_id=None, private=False):
        self.rows["job-1"] = {
            "id": "job-1",
            "cik": cik,
            "as_of": as_of,
            "decision": decision,
            "private": private,
            "status": "queued",
            "events": [],
            "report": None,
        }
        return "job-1"

    def update(self, job_id, **fields):
        if job_id in self.rows:
            self.rows[job_id].update(fields)

    def claim(self, job_id):
        return True


def test_private_status_endpoint():
    client = TestClient(app)

    # When Ollama is running and has both models
    with patch("httpx.get") as mock_get:
        mock_get.return_value = httpx.Response(
            200,
            json={"models": [{"name": "qwen2.5:1.5b"}, {"name": "gemma3:1b"}]},
        )
        resp = client.get("/api/private/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is True
        assert data["runtime"] == "ollama"
        assert set(data["models"]) == {"gemma3:1b", "qwen2.5:1.5b"}

    # When Ollama is unreachable
    with patch("httpx.get", side_effect=httpx.ConnectError("Connection refused")):
        resp = client.get("/api/private/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is False
        assert data["models"] == []


def test_start_crash_test_private_rejects_with_409_when_ollama_unavailable():
    client = TestClient(app)
    store = MockStore()

    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_optional_user] = lambda: {"id": "u-test", "role": "demo", "plan": "free"}
    app.dependency_overrides[get_inline] = lambda: True

    try:
        with patch("httpx.get", side_effect=httpx.ConnectError("Connection refused")):
            resp = client.post(
                "/api/crash-tests",
                json={"cik": "0000719739", "decision": "Partnership check with SVB", "private": True},
            )
            assert resp.status_code == 409
            assert resp.json()["detail"] == PRIVATE_UNAVAILABLE
    finally:
        app.dependency_overrides.clear()


def test_execute_in_private_mode_attaches_private_report_metadata():
    store = MockStore()
    store.create("0000719739", date(2023, 3, 10), "decision", "hash", private=True)

    def private_runner(cik, as_of, decision, on_event, private=False):
        assert private is True
        return {
            "allowed": True,
            "report": {
                "company": "SVB",
                "cik": cik,
                "as_of": str(as_of),
                "decision": decision,
                "findings": [],
            },
        }

    execute("job-1", "0000719739", date(2023, 3, 10), "decision", store, private_runner, private=True)

    job = store.rows["job-1"]
    assert job["status"] == "done"
    assert job["report"]["private"] is True
    assert "qwen2.5:1.5b" in job["report"]["private_models"]
    assert "gemma3:1b" in job["report"]["private_models"]
