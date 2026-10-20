import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.routes import execute, get_inline, get_memo_writer, get_runner, get_store
from app.auth.deps import get_optional_user, get_user_store
from app.main import app


def now():
    return datetime.now(timezone.utc)


class FakeStore:
    def __init__(self):
        self.rows = {}

    def find_done(self, cik, as_of, h):
        return next((r for r in self.rows.values()
                     if (r["cik"], r["as_of"], r["decision_hash"], r["status"]) == (cik, as_of, h, "done")), None)

    def busy(self):
        return any(r["status"] in ("queued", "running") and now() - r["updated_at"] < timedelta(minutes=10)
                   for r in self.rows.values())

    def create(self, cik, as_of, decision, h, source="live", user_id=None):
        i = str(uuid.uuid4())
        self.rows[i] = dict(id=i, cik=cik, as_of=as_of, decision=decision, decision_hash=h, status="queued",
                            events=[], report=None, memo=None, error=None, source=source, user_id=user_id,
                            created_at=now(), updated_at=now())
        return i

    def update(self, i, **fields):
        self.rows[i].update(fields, updated_at=now())

    def get(self, i):
        return self.rows.get(i)

    def claim(self, i):
        if self.rows[i]["status"] != "queued":
            return False
        self.rows[i].update(status="running", updated_at=now())
        return True

    def companies(self):
        return [{"cik": "0000719739", "company": "SVB FINANCIAL GROUP", "filing_count": 4, "chunk_count": 900,
                 "filings": [], "crash_tests": [r for r in self.rows.values() if r["status"] == "done"]}]


def ok_runner(cik, as_of, decision, on_event):
    on_event([{"node": "redact", "message": "No personal data found", "ms": 1}])
    on_event([{"node": "score", "message": "Health 42/100", "ms": 2}])
    return {"allowed": True, "report": {"cik": cik, "company": "SVB", "as_of": as_of.isoformat(), "decision": decision,
                                        "findings": [], "health": {"score": 42}}}


MEMO_CALLS = []


class Usage:
    def __init__(self, used=0):
        self.used = used

    def usage_this_month(self, user_id):
        return self.used


DEMO = {"id": "u-demo", "role": "demo", "plan": "free"}
USAGE = Usage()


def fake_writer(report):
    MEMO_CALLS.append(report["cik"])
    return {"company": report["company"], "as_of": report["as_of"], "decision": report["decision"],
            "status": "complete", "status_note": "", "health": None, "executive_summary": "summary",
            "risks": [], "evidence_gaps": [], "disclaimer": "not legal advice", "dropped": [], "usage": None}


@pytest.fixture
def client_store():
    def make(runner=ok_runner, writer=fake_writer):
        store = FakeStore()
        app.dependency_overrides[get_store] = lambda: store
        app.dependency_overrides[get_runner] = lambda: runner
        app.dependency_overrides[get_memo_writer] = lambda: writer
        app.dependency_overrides[get_optional_user] = lambda: DEMO
        app.dependency_overrides[get_user_store] = lambda: USAGE
        MEMO_CALLS.clear()
        return TestClient(app), store
    yield make
    app.dependency_overrides.clear()


def start(client, **body):
    return client.post("/api/crash-tests", json={"cik": "719739", "as_of": "2023-03-10", **body})


def test_start_then_poll_until_done(client_store):
    client, _ = client_store()
    r = start(client, decision="Deposit partnership")
    assert r.status_code == 202 and r.json()["cached"] is False
    job = client.get(f"/api/crash-tests/{r.json()['id']}").json()
    assert job["status"] == "done" and job["cik"] == "0000719739"
    assert job["report"]["health"]["score"] == 42
    assert job["done_nodes"] == ["redact", "score"] and job["pipeline"][0] == "redact"


def test_same_decision_is_served_from_cache(client_store):
    client, _ = client_store()
    first = start(client, decision="Deposit  partnership").json()
    again = client.post("/api/crash-tests", json={"cik": "0000719739", "as_of": "2023-03-10", "decision": "deposit partnership "})
    assert again.status_code == 200 and again.json() == {"id": first["id"], "status": "done", "cached": True, "worker_online": None}


def test_decision_is_redacted_before_storage_and_model(client_store):
    client, store = client_store()
    r = client.post("/api/crash-tests", json={"cik": "719739", "decision": "Email cfo@partner.com before we sign"})
    row = store.rows[r.json()["id"]]
    assert row["decision"] == "Email [EMAIL] before we sign" and "partner.com" not in str(row["report"])


def test_validation_errors(client_store):
    client, _ = client_store()
    assert client.post("/api/crash-tests", json={"cik": "abc"}).status_code == 422
    future = (date.today() + timedelta(days=2)).isoformat()
    assert client.post("/api/crash-tests", json={"cik": "1", "as_of": future}).status_code == 422
    assert client.post("/api/crash-tests", json={"cik": "1", "decision": "x" * 1501}).status_code == 422


def test_busy_server_answers_429(client_store):
    client, store = client_store()
    store.create("0000000001", date.today(), "", "other")
    r = client.post("/api/crash-tests", json={"cik": "719739", "decision": "new"})
    assert r.status_code == 429 and "precomputed demo" in r.json()["detail"]


def test_runner_error_marks_job_failed(client_store):
    def broken(cik, as_of, decision, on_event):
        on_event([{"node": "redact", "message": "ok", "ms": 1}])
        raise RuntimeError("Neo4j unreachable\nstack details")
    client, _ = client_store(broken)
    job = client.get(f"/api/crash-tests/{start(client).json()['id']}").json()
    assert job["status"] == "failed" and job["error"] == "RuntimeError: Neo4j unreachable"
    assert job["done_nodes"] == ["redact"]


def test_guard_block_is_reported(client_store):
    def blocked(cik, as_of, decision, on_event):
        return {"allowed": False, "guard_result": {"category": "prompt_injection", "reason": "Instruction-override pattern detected."}}
    client, _ = client_store(blocked)
    job = client.get(f"/api/crash-tests/{start(client).json()['id']}").json()
    assert job["status"] == "blocked" and "Instruction-override" in job["error"]


def test_unknown_and_stale_jobs(client_store):
    client, store = client_store()
    assert client.get("/api/crash-tests/not-a-uuid").status_code == 404
    assert client.get(f"/api/crash-tests/{uuid.uuid4()}").status_code == 404
    i = store.create("0000000001", date.today(), "", "h")
    store.rows[i].update(status="running", updated_at=now() - timedelta(minutes=20))
    job = client.get(f"/api/crash-tests/{i}").json()
    assert job["status"] == "failed" and "Timed out" in job["error"]


def test_memo_created_once_then_cached(client_store):
    client, _ = client_store()
    job_id = start(client, decision="Deposit partnership").json()["id"]
    assert client.get(f"/api/crash-tests/{job_id}/memo").status_code == 404
    first = client.post(f"/api/crash-tests/{job_id}/memo").json()
    assert first["cached"] is False and first["memo"]["status"] == "complete"
    assert "# Legal Risk Memo: SVB" in first["markdown"] and "not legal advice" in first["markdown"]
    second = client.post(f"/api/crash-tests/{job_id}/memo").json()
    assert second["cached"] is True and MEMO_CALLS == ["0000719739"]
    assert client.get(f"/api/crash-tests/{job_id}/memo").json()["cached"] is True


def test_memo_needs_finished_crash_test(client_store):
    client, store = client_store()
    i = store.create("0000000001", date.today(), "", "h")
    r = client.post(f"/api/crash-tests/{i}/memo")
    assert r.status_code == 409 and "not finished" in r.json()["detail"]


def test_unavailable_memo_is_not_cached(client_store):
    def down(report):
        return {**fake_writer(report), "status": "unavailable", "status_note": "rate limited"}
    client, store = client_store(writer=down)
    job_id = start(client).json()["id"]
    assert client.post(f"/api/crash-tests/{job_id}/memo").json()["memo"]["status"] == "unavailable"
    assert store.rows[job_id]["memo"] is None


def test_companies_lists_finished_runs(client_store):
    client, _ = client_store()
    start(client, decision="Deposit partnership")
    data = client.get("/api/companies").json()
    assert data[0]["company"] == "SVB FINANCIAL GROUP" and len(data[0]["crash_tests"]) == 1


def test_evaluation_results_are_served():
    r = TestClient(app).get("/api/evaluation")
    assert r.status_code == 200 and "pii" in r.json() and "injection" in r.json()

class QueueStore(FakeStore):
    def __init__(self, worker=True):
        super().__init__()
        self.worker = worker

    def claim_next(self):
        queued = sorted((r for r in self.rows.values() if r["status"] == "queued"), key=lambda r: r["created_at"])
        if not queued:
            return None
        queued[0].update(status="running", updated_at=now())
        return {k: queued[0][k] for k in ("id", "cik", "as_of", "decision")}

    def worker_online(self):
        return {"last_seen": now(), "current_job": None, "rerank_enabled": True} if self.worker else None


def queue_client(store):
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_inline] = lambda: False
    app.dependency_overrides[get_runner] = lambda: ok_runner
    app.dependency_overrides[get_optional_user] = lambda: DEMO
    app.dependency_overrides[get_user_store] = lambda: USAGE
    return TestClient(app)


def test_queue_mode_only_queues_then_worker_runs_it():
    store = QueueStore()
    try:
        client = queue_client(store)
        r = start(client, decision="Deposit partnership").json()
        assert r["status"] == "queued" and r["worker_online"] is True
        assert store.rows[r["id"]]["status"] == "queued"            # the API did not run it
        job = store.claim_next()
        assert job["id"] == r["id"] and store.claim_next() is None   # claimed once
        execute(job["id"], job["cik"], job["as_of"], job["decision"], store, ok_runner)
        polled = client.get(f"/api/crash-tests/{r['id']}").json()
        assert polled["status"] == "done" and polled["report"]["retrieval_mode"].startswith("hybrid")
    finally:
        app.dependency_overrides.clear()


def test_queued_job_without_worker_fails_after_timeout():
    store = QueueStore(worker=False)
    try:
        client = queue_client(store)
        r = start(client).json()
        assert r["worker_online"] is False
        assert client.get(f"/api/crash-tests/{r['id']}").json()["worker_online"] is False
        store.rows[r["id"]]["created_at"] = now() - timedelta(minutes=6)
        job = client.get(f"/api/crash-tests/{r['id']}").json()
        assert job["status"] == "failed" and "No analysis worker" in job["error"]
    finally:
        app.dependency_overrides.clear()


def test_status_endpoint_reports_worker():
    try:
        client = queue_client(QueueStore(worker=True))
        s = client.get("/api/status").json()
        assert s["live_mode"] == "worker" and s["worker_online"] is True and s["rerank_enabled"] is True
        app.dependency_overrides[get_store] = lambda: QueueStore(worker=False)
        s = client.get("/api/status").json()
        assert s["worker_online"] is False and s["worker"] is None
    finally:
        app.dependency_overrides.clear()

def test_inline_run_skips_a_job_a_worker_already_claimed(client_store):
    from app.api.routes import execute_claimed
    client, store = client_store()
    i = store.create("0000719739", date(2023, 3, 10), "d", "h")
    store.rows[i]["status"] = "running"            # a worker claimed it first
    calls = []
    execute_claimed(i, "0000719739", date(2023, 3, 10), "d", store, lambda *a: calls.append(1) or {})
    assert calls == [] and store.rows[i]["status"] == "running"

def test_new_run_needs_login_but_cached_demo_does_not(client_store):
    client, store = client_store()
    first = start(client, decision="Deposit partnership").json()
    app.dependency_overrides[get_optional_user] = lambda: None
    cached = start(client, decision="Deposit partnership")
    assert cached.status_code == 200 and cached.json()["id"] == first["id"]
    new = start(client, decision="Something new")
    assert new.status_code == 401 and "demo account" in new.json()["detail"]


def test_free_plan_limit_is_enforced_and_demo_is_unlimited(client_store):
    client, store = client_store()
    app.dependency_overrides[get_optional_user] = lambda: {"id": "u1", "role": "user", "plan": "free"}
    app.dependency_overrides[get_user_store] = lambda: Usage(used=3)
    r = start(client, decision="fourth run")
    assert r.status_code == 403 and "Free plan includes 3" in r.json()["detail"]
    app.dependency_overrides[get_optional_user] = lambda: DEMO
    assert start(client, decision="fourth run").status_code == 202
    assert any(row.get("user_id") == "u-demo" for row in store.rows.values())