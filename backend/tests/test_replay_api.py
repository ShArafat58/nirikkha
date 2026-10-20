from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_cases_includes_svb():
    r = client.get("/api/replay")
    assert r.status_code == 200
    assert "svb" in [c["id"] for c in r.json()["cases"]]


def test_case_timeline_marks_frozen_events():
    r = client.get("/api/replay/svb")
    assert r.status_code == 200
    body = r.json()
    vis = {e["id"]: e["visible_at_freeze"] for e in body["case"]["timeline"]}
    assert vis["ev_pre14a_2023"] is True
    assert vis["ev_failure"] is False
    assert len(body["case"]["warning_signs"]) == 6


def test_bad_case_ids_are_404():
    assert client.get("/api/replay/nope").status_code == 404
    assert client.get("/api/replay/..%2Fsecrets").status_code == 404