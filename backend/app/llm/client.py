"""LLM client with task-based model routing, rate-limit budgets, fallback, response cache and usage log.

Providers: Groq (OpenAI-compatible API), Gemini (generateContent), Ollama (local, optional).
Each task has an ordered route. Before calling a model, the client checks that model's
per-minute and per-day budget (LIMITS): it waits if the minute window is full (up to
max_wait seconds, configurable per call), or skips to the next model if the wait is too long
or the daily tokens are used up. The minute window counts the full reserved request size
(prompt + max output), like the providers do. On HTTP 429 with "try again in Xs", the client
waits X seconds and retries the same model once. Other failures (server error, timeout, empty
or invalid JSON output) move to the next model, so the demo never dies.

Every call is logged to backend/.cache/llm_usage.jsonl (task, provider, model, tokens,
latency, cache hit, cost). Daily budgets are rebuilt from this log on start.
Free-tier calls cost $0; PRICES (USD per 1M tokens) is filled only from official pricing pages.

Run directly:
    python -m app.llm.client --task fast "Reply with exactly one word: ok"
    python -m app.llm.client --task extract --json "Return JSON with keys name and role for: ..."
    python -m app.llm.client --budget
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable

import httpx

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Ordered fallbacks per task. Change models only here.
# The local Ollama model is a placeholder until the local runtime is set up (Day 7).
ROUTES: dict[str, list[tuple[str, str]]] = {
    "reason": [("groq", "openai/gpt-oss-120b"), ("gemini", "gemini-2.5-flash"), ("ollama", "qwen2.5:3b")],
    "fast": [("groq", "openai/gpt-oss-20b"), ("gemini", "gemini-2.5-flash-lite"), ("ollama", "qwen2.5:3b")],
    "extract": [("groq", "qwen/qwen3.8-27b"), ("groq", "openai/gpt-oss-20b"), ("gemini", "gemini-2.5-flash"),
                ("ollama", "qwen2.5:3b")],
    "safety": [("groq", "openai/gpt-oss-safeguard-20b"), ("groq", "openai/gpt-oss-20b")],
    "bangla": [("gemini", "gemini-2.5-flash"), ("groq", "qwen/qwen3.8-27b")],
}

# Free-tier limits. Groq values measured on 2026-10-20 at console.groq.com/settings/limits.
# Gemini values are ASSUMED (not visible on ai.dev/rate-limit for this project) and kept conservative.
# tpd = 0 means no client-side daily token cap.
LIMITS: dict[str, dict[str, int]] = {
    "openai/gpt-oss-120b": {"rpm": 30, "tpm": 8000, "tpd": 200000},
    "openai/gpt-oss-20b": {"rpm": 30, "tpm": 8000, "tpd": 200000},
    "qwen/qwen3.8-27b": {"rpm": 30, "tpm": 8000, "tpd": 200000},
    "openai/gpt-oss-safeguard-20b": {"rpm": 3, "tpm": 2000, "tpd": 200000},
    "gemini-2.5-flash": {"rpm": 10, "tpm": 250000, "tpd": 0},
    "gemini-2.5-flash-lite": {"rpm": 15, "tpm": 250000, "tpd": 0},
}
SAFETY_MARGIN = 0.9  # use at most 90% of each limit

# USD per 1M tokens: {"model": (input, output)}. Empty = free tier, cost $0. Fill only from official pricing pages.
PRICES: dict[str, tuple[float, float]] = {}

REASONING_EFFORT = {"reason": "medium", "fast": "low", "extract": "low", "safety": "low", "bangla": "low"}

_RETRY_RE = re.compile(r"try again in (?:(\d+)m)?([\d.]+)(ms|s)", re.I)


class LLMError(RuntimeError):
    """All providers in the route failed."""


class _ProviderError(Exception):
    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


@dataclass
class LLMResult:
    text: str
    data: Any
    task: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cached: bool
    cost_usd: float
    attempts: list[str] = field(default_factory=list)


def parse_json(text: str) -> Any | None:
    """Parse JSON from model output, tolerating ```json fences and surrounding prose."""
    cleaned = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text.strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.S)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


def parse_retry_after(headers: httpx.Headers, body: str) -> float | None:
    """Seconds to wait from a Retry-After header or a 'try again in 1m2.5s' message."""
    header = headers.get("retry-after")
    if header:
        try:
            return float(header)
        except ValueError:
            pass
    match = _RETRY_RE.search(body)
    if match:
        minutes = int(match.group(1) or 0)
        value = float(match.group(2))
        if match.group(3).lower() == "ms":
            value /= 1000.0
        return minutes * 60 + value
    return None


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    price = PRICES.get(model)
    if not price:
        return 0.0
    return round(input_tokens / 1e6 * price[0] + output_tokens / 1e6 * price[1], 6)


def estimate_request_tokens(messages: list[dict[str, str]], max_tokens: int) -> int:
    """Reserved request size used for budgeting: prompt (~3 chars/token) + max output."""
    return sum(len(m["content"]) for m in messages) // 3 + max_tokens


class _Budget:
    """Per-model rolling minute window (reserved tokens) + per-day totals (actual tokens)."""

    def __init__(self, limits: dict[str, dict[str, int]], clock: Callable[[], float] = time.monotonic) -> None:
        self.limits = limits
        self.clock = clock
        self.window: dict[str, deque[tuple[float, int]]] = {}
        self.day = date.today()
        self.day_tokens: dict[str, int] = {}

    def _roll_day(self) -> None:
        if date.today() != self.day:
            self.day = date.today()
            self.day_tokens = {}

    def wait_seconds(self, model: str, est_tokens: int) -> float | None:
        """0 = go now; >0 = seconds to wait for the minute window; None = daily budget used up."""
        limit = self.limits.get(model)
        if not limit:
            return 0.0
        self._roll_day()
        tpd = limit.get("tpd", 0)
        if tpd and self.day_tokens.get(model, 0) + est_tokens > tpd * SAFETY_MARGIN:
            return None
        now = self.clock()
        win = self.window.setdefault(model, deque())
        while win and now - win[0][0] >= 60:
            win.popleft()
        used = sum(t for _, t in win)
        rpm_ok = len(win) < limit.get("rpm", 10**9) * SAFETY_MARGIN
        tpm_ok = used + est_tokens <= limit.get("tpm", 10**12) * SAFETY_MARGIN
        if (rpm_ok and tpm_ok) or not win:
            return 0.0
        return max(0.5, 60 - (now - win[0][0]) + 0.5)

    def record(self, model: str, reserved_tokens: int, actual_tokens: int) -> None:
        self._roll_day()
        self.window.setdefault(model, deque()).append((self.clock(), reserved_tokens))
        self.day_tokens[model] = self.day_tokens.get(model, 0) + actual_tokens

    def load_today(self, usage_log: Path | None) -> None:
        if usage_log is None or not usage_log.exists():
            return
        today = date.today().isoformat()
        for line in usage_log.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("ts", "").startswith(today) and not row.get("cached"):
                model = row.get("model", "")
                self.day_tokens[model] = self.day_tokens.get(model, 0) + row.get("input_tokens", 0) + row.get("output_tokens", 0)


class LLMClient:
    def __init__(
        self,
        groq_key: str = "",
        gemini_key: str = "",
        ollama_url: str = "http://localhost:11434",
        cache_dir: Path | None = None,
        usage_log: Path | None = None,
        transport: httpx.BaseTransport | None = None,
        routes: dict[str, list[tuple[str, str]]] | None = None,
        limits: dict[str, dict[str, int]] | None = None,
        timeout: float = 90.0,
        max_wait: float = 20.0,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.groq_key = groq_key
        self.gemini_key = gemini_key
        self.ollama_url = ollama_url.rstrip("/")
        self.cache_dir = cache_dir
        self.usage_log = usage_log
        self.routes = routes or ROUTES
        self.max_wait = max_wait
        self._sleep = sleep
        self.budget = _Budget(LIMITS if limits is None else limits, clock)
        self.budget.load_today(usage_log)
        self._http = httpx.Client(timeout=timeout, transport=transport)

    def close(self) -> None:
        self._http.close()

    # ---------- cache ----------
    def _cache_path(self, provider: str, model: str, payload: dict) -> Path | None:
        if self.cache_dir is None:
            return None
        key = hashlib.sha256(json.dumps([provider, model, payload], sort_keys=True).encode("utf-8")).hexdigest()
        return self.cache_dir / key[:2] / f"{key}.json"

    # ---------- usage log ----------
    def _log(self, result: LLMResult) -> None:
        if self.usage_log is None:
            return
        self.usage_log.parent.mkdir(parents=True, exist_ok=True)
        row = {k: v for k, v in asdict(result).items() if k not in ("text", "data")}
        row["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self.usage_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")

    # ---------- providers ----------
    def _post(self, url: str, **kwargs) -> dict:
        try:
            resp = self._http.post(url, **kwargs)
        except httpx.HTTPError as exc:
            raise _ProviderError(f"network error: {exc.__class__.__name__}") from exc
        if resp.status_code != 200:
            retry = parse_retry_after(resp.headers, resp.text) if resp.status_code == 429 else None
            raise _ProviderError(f"HTTP {resp.status_code}: {resp.text[:400]}", retry_after=retry)
        return resp.json()

    def _call_groq(self, task, model, messages, json_mode, max_tokens, temperature):
        if not self.groq_key:
            raise _ProviderError("GROQ_API_KEY not set")
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_completion_tokens": max_tokens,
            "temperature": temperature,
        }
        if "gpt-oss" in model:
            body["reasoning_effort"] = REASONING_EFFORT.get(task, "low")
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        data = self._post(GROQ_URL, json=body, headers={"Authorization": f"Bearer {self.groq_key}"})
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        usage = data.get("usage", {})
        return text, int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))

    def _call_gemini(self, task, model, messages, json_mode, max_tokens, temperature):
        if not self.gemini_key:
            raise _ProviderError("GEMINI_API_KEY not set")
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        contents = [
            {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
            for m in messages if m["role"] != "system"
        ]
        config: dict[str, Any] = {"maxOutputTokens": max_tokens, "temperature": temperature}
        if json_mode:
            config["responseMimeType"] = "application/json"
        if model.startswith("gemini-2.5-flash"):
            config["thinkingConfig"] = {"thinkingBudget": 0}  # no hidden thinking tokens for routine tasks
        body: dict[str, Any] = {"contents": contents, "generationConfig": config}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        data = self._post(GEMINI_URL.format(model=model), json=body, headers={"x-goog-api-key": self.gemini_key})
        parts = ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts)
        usage = data.get("usageMetadata", {})
        out_tokens = int(usage.get("candidatesTokenCount", 0)) + int(usage.get("thoughtsTokenCount", 0))
        return text, int(usage.get("promptTokenCount", 0)), out_tokens

    def _call_ollama(self, task, model, messages, json_mode, max_tokens, temperature):
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if json_mode:
            body["format"] = "json"
        data = self._post(f"{self.ollama_url}/api/chat", json=body)
        text = data.get("message", {}).get("content", "")
        return text, int(data.get("prompt_eval_count", 0)), int(data.get("eval_count", 0))

    # ---------- public ----------
    def complete(
        self,
        task: str,
        messages: list[dict[str, str]],
        json_mode: bool = False,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        use_cache: bool = True,
        max_wait: float | None = None,
    ) -> LLMResult:
        """Run a task through its route. max_wait overrides how long to wait for a busy model."""
        if task not in self.routes:
            raise LLMError(f"Unknown task {task!r}. Known: {sorted(self.routes)}")
        limit_wait = self.max_wait if max_wait is None else max_wait
        payload = {"messages": messages, "json": json_mode, "max_tokens": max_tokens, "temperature": temperature}
        attempts: list[str] = []
        callers = {"groq": self._call_groq, "gemini": self._call_gemini, "ollama": self._call_ollama}
        est_tokens = estimate_request_tokens(messages, max_tokens)

        for provider, model in self.routes[task]:
            path = self._cache_path(provider, model, payload) if use_cache else None
            if path is not None and path.exists():
                cached = json.loads(path.read_text(encoding="utf-8"))
                result = LLMResult(**{**cached, "cached": True, "latency_ms": 0, "cost_usd": 0.0, "attempts": attempts})
                self._log(result)
                return result

            retried = False
            while True:
                wait = self.budget.wait_seconds(model, est_tokens)
                if wait is None:
                    attempts.append(f"{provider}:{model} -> daily token budget used")
                    break
                if wait > limit_wait:
                    attempts.append(f"{provider}:{model} -> minute window busy ({wait:.0f}s)")
                    break
                if wait > 0:
                    self._sleep(wait)

                started = time.perf_counter()
                try:
                    text, tokens_in, tokens_out = callers[provider](task, model, messages, json_mode, max_tokens, temperature)
                except _ProviderError as exc:
                    if exc.retry_after is not None and not retried and exc.retry_after <= limit_wait:
                        retried = True
                        self._sleep(exc.retry_after + 0.5)
                        continue
                    attempts.append(f"{provider}:{model} -> {exc}")
                    break
                latency = int((time.perf_counter() - started) * 1000)
                self.budget.record(model, est_tokens, tokens_in + tokens_out)

                if not text.strip():
                    attempts.append(f"{provider}:{model} -> empty output")
                    break
                data = None
                if json_mode:
                    data = parse_json(text)
                    if data is None:
                        attempts.append(f"{provider}:{model} -> invalid JSON")
                        break

                result = LLMResult(
                    text=text, data=data, task=task, provider=provider, model=model,
                    input_tokens=tokens_in, output_tokens=tokens_out, latency_ms=latency, cached=False,
                    cost_usd=cost_usd(model, tokens_in, tokens_out), attempts=attempts,
                )
                if path is not None:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps(asdict(result)), encoding="utf-8")
                self._log(result)
                return result

        raise LLMError(f"All providers failed for task {task!r}: " + " | ".join(attempts))

    def budget_report(self) -> list[dict]:
        rows = []
        for model, limit in self.budget.limits.items():
            used = self.budget.day_tokens.get(model, 0)
            tpd = limit.get("tpd", 0)
            rows.append({"model": model, "used_today": used, "tpd": tpd,
                         "pct": round(100.0 * used / tpd, 1) if tpd else None})
        return rows


_client: LLMClient | None = None


def get_llm() -> LLMClient:
    """Process-wide client configured from settings."""
    global _client
    if _client is None:
        from app.config import get_settings

        s = get_settings()
        _client = LLMClient(
            groq_key=s.groq_api_key,
            gemini_key=s.gemini_api_key,
            ollama_url=s.ollama_url,
            cache_dir=s.cache_dir / "llm_cache",
            usage_log=s.cache_dir / "llm_usage.jsonl",
        )
    return _client


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Call the LLM router")
    parser.add_argument("prompt", nargs="?")
    parser.add_argument("--task", default="fast", choices=sorted(ROUTES))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--budget", action="store_true", help="show today's token use per model")
    args = parser.parse_args(argv[1:])

    if args.budget:
        for row in get_llm().budget_report():
            pct = f"{row['pct']}%" if row["pct"] is not None else "no daily cap"
            print(f"  {row['model']:32} used today {row['used_today']:>8,} / {row['tpd'] or '-':>8}  ({pct})")
        return 0
    if not args.prompt:
        parser.error("prompt is required unless --budget is used")

    system = "You are a careful governance analyst."
    if args.json:
        system += " Respond only with a valid JSON object."
    messages = [{"role": "system", "content": system}, {"role": "user", "content": args.prompt}]
    try:
        r = get_llm().complete(args.task, messages, json_mode=args.json, use_cache=not args.no_cache)
    except LLMError as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"task={r.task} provider={r.provider} model={r.model} tokens_in={r.input_tokens} "
          f"tokens_out={r.output_tokens} latency_ms={r.latency_ms} cached={r.cached} cost_usd={r.cost_usd}")
    if r.attempts:
        print("fallbacks: " + " | ".join(r.attempts))
    print("---")
    print(json.dumps(r.data, ensure_ascii=False, indent=2) if r.data is not None else r.text)
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))