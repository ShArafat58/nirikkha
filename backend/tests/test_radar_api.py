import pytest
from fastapi.testclient import TestClient

from app.api.radar_routes import get_radar_store
from app.auth.deps import get_current_user
from app.main import app
from app.radar.store import InMemoryRadarStore


@pytest.fixture
def store():
    s = InMemoryRadarStore()
    s.upsert([
        {"key": "reg:x:1", "stream": "regulatory", "cik": "1", "company": "Co", "title": "Rule X",
         "priority": "high", "event_date": "2024-01-01", "evidence": {"status": "gap", "passage": None}},
        {"key": "filing:y", "stream": "filing", "cik": "1", "company": "Co", "title": "New 8-K",
         "priority": "medium", "event_date": "2025-01-01", "evidence": {"status": "not_analysed", "passage": None}},
    ])
    app.dependency_overrides[get_radar_store] = lambda: s
    yield s
    app.dependency_overrides.clear()


client = TestClient(app)


def test_list_is_public_and_prioritised(store):
    r = client.get("/api/radar")
    assert r.status_code == 200
    body = r.json()
    assert [a["title"] for a in body["alerts"]] == ["Rule X", "New 8-K"]
    assert body["summary"]["pending"] == 2 and body["summary"]["by_stream"] == {"regulatory": 1, "filing": 1}


def test_decision_requires_login(store):
    alert_id = store.list()[0]["id"]
    r = client.post(f"/api/radar/alerts/{alert_id}/decision", json={"decision": "approve"})
    assert r.status_code in (401, 403)
    assert store.get(alert_id)["status"] == "pending"


def test_decision_is_saved_with_audit_trail(store):
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "email": "analyst@example.com"}
    alert_id = store.list()[0]["id"]
    r = client.post(f"/api/radar/alerts/{alert_id}/decision", json={"decision": "reject", "note": "not material"})
    assert r.status_code == 200
    assert r.json()["alert"]["status"] == "rejected"
    h = client.get(f"/api/radar/alerts/{alert_id}/history").json()["history"]
    assert h == [{"decision": "rejected", "note": "not material", "by": "a***@example.com", "at": "t0"}]


def test_bad_decision_and_unknown_alert(store):
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "email": "a@b.co"}
    alert_id = store.list()[0]["id"]
    assert client.post(f"/api/radar/alerts/{alert_id}/decision", json={"decision": "maybe"}).status_code == 422
    assert client.post("/api/radar/alerts/nope/decision", json={"decision": "approve"}).status_code == 404


def test_scan_needs_the_token(store, monkeypatch):
    monkeypatch.delenv("RADAR_SCAN_TOKEN", raising=False)
    assert client.post("/api/radar/scan").status_code == 503
    monkeypatch.setenv("RADAR_SCAN_TOKEN", "s3cret")
    assert client.post("/api/radar/scan", headers={"X-Radar-Token": "wrong"}).status_code == 401
    from app.radar import engine
    monkeypatch.setattr(engine, "scan", lambda use_edgar=True: [])
    r = client.post("/api/radar/scan", headers={"X-Radar-Token": "s3cret"})
    assert r.status_code == 200 and r.json()["saved"] == 0