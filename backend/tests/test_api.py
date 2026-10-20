import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.routes import get_runner, get_store
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

    def create(self, cik, as_of, decision, h, source="live"):
        i = str(uuid.uuid4())
        self.rows[i] = dict(id=i, cik=cik, as_of=as_of, decision=decision, decision_hash=h, status="queued",
                            events=[], report=None, error=None, source=source, created_at=now(), updated_at=now())
        return i

    def update(self, i, **fields):
        self.rows[i].update(fields, updated_at=now())

    def get(self, i):
        return self.rows.get(i)


def ok_runner(cik, as_of, decision, on_event):
    on_event([{"node": "redact", "message": "No personal data found", "ms": 1}])
    on_event([{"node": "score", "message": "Health 42/100", "ms": 2}])
    return {"allowed": True, "report": {"cik": cik, "decision": decision, "health": {"score": 42}}}


@pytest.fixture
def client_store():
    def make(runner=ok_runner):
        store = FakeStore()
        app.dependency_overrides[get_store] = lambda: store
        app.dependency_overrides[get_runner] = lambda: runner
        return TestClient(app), store
    yield make
    app.dependency_overrides.clear()


def test_start_then_poll_until_done(client_store):
    client, store = client_store()
    r = client.post("/api/crash-tests", json={"cik": "719739", "as_of": "2023-03-10", "decision": "Deposit partnership"})
    assert r.status_code == 202 and r.json()["cached"] is False
    job = client.get(f"/api/crash-tests/{r.json()['id']}").json()
    assert job["status"] == "done" and job["cik"] == "0000719739"
    assert job["report"]["health"]["score"] == 42
    assert job["done_nodes"] == ["redact", "score"] and job["pipeline"][0] == "redact"


def test_same_decision_is_served_from_cache(client_store):
    client, _ = client_store()
    first = client.post("/api/crash-tests", json={"cik": "719739", "as_of": "2023-03-10", "decision": "Deposit  partnership"}).json()
    again = client.post("/api/crash-tests", json={"cik": "0000719739", "as_of": "2023-03-10", "decision": "deposit partnership "})
    assert again.status_code == 200 and again.json() == {"id": first["id"], "status": "done", "cached": True}


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
    job = client.get(f"/api/crash-tests/{client.post('/api/crash-tests', json={'cik': '1'}).json()['id']}").json()
    assert job["status"] == "failed" and job["error"] == "RuntimeError: Neo4j unreachable"
    assert job["done_nodes"] == ["redact"]


def test_guard_block_is_reported(client_store):
    def blocked(cik, as_of, decision, on_event):
        return {"allowed": False, "guard_result": {"category": "prompt_injection", "reason": "Instruction-override pattern detected."}}
    client, _ = client_store(blocked)
    job = client.get(f"/api/crash-tests/{client.post('/api/crash-tests', json={'cik': '1'}).json()['id']}").json()
    assert job["status"] == "blocked" and "Instruction-override" in job["error"]


def test_unknown_and_stale_jobs(client_store):
    client, store = client_store()
    assert client.get("/api/crash-tests/not-a-uuid").status_code == 404
    assert client.get(f"/api/crash-tests/{uuid.uuid4()}").status_code == 404
    i = store.create("0000000001", date.today(), "", "h")
    store.rows[i].update(status="running", updated_at=now() - timedelta(minutes=20))
    job = client.get(f"/api/crash-tests/{i}").json()
    assert job["status"] == "failed" and "Timed out" in job["error"]