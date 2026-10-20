"""Offline tests for the LLM router (fake providers, no network)."""

import json

import httpx
import pytest

from app.llm.client import LLMClient, LLMError, parse_json

ROUTES = {"t": [("groq", "g-model"), ("gemini", "gem-model"), ("ollama", "local-model")]}
MSG = [{"role": "system", "content": "Respond in JSON."}, {"role": "user", "content": "hi"}]


def groq_ok(text):
    return httpx.Response(200, json={"choices": [{"message": {"content": text}}],
                                     "usage": {"prompt_tokens": 10, "completion_tokens": 5}})


def gemini_ok(text):
    return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": text}]}}],
                                     "usageMetadata": {"promptTokenCount": 8, "candidatesTokenCount": 4}})


def make_client(handler, tmp_path=None):
    return LLMClient(
        groq_key="gk", gemini_key="mk", routes=ROUTES,
        cache_dir=(tmp_path / "cache") if tmp_path else None,
        usage_log=(tmp_path / "usage.jsonl") if tmp_path else None,
        transport=httpx.MockTransport(handler),
    )


def test_groq_success_is_logged(tmp_path):
    client = make_client(lambda r: groq_ok("hello"), tmp_path)
    result = client.complete("t", MSG)
    assert (result.provider, result.text, result.input_tokens, result.output_tokens) == ("groq", "hello", 10, 5)
    row = json.loads((tmp_path / "usage.jsonl").read_text().splitlines()[0])
    assert row["provider"] == "groq" and row["cost_usd"] == 0.0


def test_falls_back_to_gemini_on_rate_limit():
    def handler(request):
        if "groq" in request.url.host:
            return httpx.Response(429, json={"error": "rate limit"})
        return gemini_ok("from gemini")

    result = make_client(handler).complete("t", MSG)
    assert result.provider == "gemini"
    assert "HTTP 429" in result.attempts[0]


def test_json_mode_falls_back_on_invalid_json():
    def handler(request):
        if "groq" in request.url.host:
            return groq_ok("not json at all")
        return gemini_ok('{"a": 1}')

    result = make_client(handler).complete("t", MSG, json_mode=True)
    assert result.data == {"a": 1}
    assert "invalid JSON" in result.attempts[0]


def test_second_identical_call_is_cached(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        return groq_ok("hello")

    client = make_client(handler, tmp_path)
    client.complete("t", MSG)
    second = client.complete("t", MSG)
    assert second.cached is True
    assert len(calls) == 1


def test_all_providers_fail_raises():
    def handler(request):
        if request.url.host == "localhost":
            raise httpx.ConnectError("refused", request=request)
        return httpx.Response(500, text="boom")

    with pytest.raises(LLMError, match="All providers failed"):
        make_client(handler).complete("t", MSG)


def test_parse_json_handles_fences_and_prose():
    assert parse_json('```json\n{"x": 2}\n```') == {"x": 2}
    assert parse_json('Here you go: {"y": 3} thanks') == {"y": 3}
    assert parse_json("no json here") is None

def test_daily_budget_used_skips_provider_without_calling_it():
    groq_calls = []

    def handler(request):
        if "groq" in request.url.host:
            groq_calls.append(request)
            return groq_ok("should not be called")
        return gemini_ok("gemini answer")

    client = LLMClient(groq_key="gk", gemini_key="mk", routes=ROUTES,
                       limits={"g-model": {"rpm": 30, "tpm": 8000, "tpd": 10}},
                       transport=httpx.MockTransport(handler))
    result = client.complete("t", MSG, max_tokens=50)
    assert result.provider == "gemini"
    assert groq_calls == []
    assert "daily token budget used" in result.attempts[0]


def test_minute_window_waits_then_calls():
    sleeps = []
    client = LLMClient(groq_key="gk", gemini_key="mk", routes=ROUTES,
                       limits={"g-model": {"rpm": 30, "tpm": 70, "tpd": 0}},
                       transport=httpx.MockTransport(lambda r: groq_ok("ok")),
                       sleep=sleeps.append, clock=lambda: 1000.0, max_wait=120)
    client.complete("t", MSG, max_tokens=50, use_cache=False)
    second = client.complete("t", MSG, max_tokens=50, use_cache=False)
    assert second.provider == "groq"
    assert sleeps and sleeps[0] > 0
