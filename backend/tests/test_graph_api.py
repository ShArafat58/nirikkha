from fastapi.testclient import TestClient

from app.api.graph_routes import build, get_graph_reader
from app.main import app

client = TestClient(app)

ROLES = [
    {"company": "Co", "pk": "a", "pn": "Ann", "rel": "DIRECTOR_OF", "title": None, "page": 10, "quote": "Ann is a director"},
    {"company": "Co", "pk": "b", "pn": "Bob", "rel": "OFFICER_OF", "title": "CFO", "page": 40, "quote": "Bob, CFO"},
    {"company": "Co", "pk": "b", "pn": "Bob", "rel": "DIRECTOR_OF", "title": None, "page": 11, "quote": "Bob is a director"},
]
COMMITTEES = [{"pk": "a", "pn": "Ann", "kk": "k1", "kn": "Audit Committee", "chair": True, "page": 12, "quote": "Ann chairs Audit"}]
OUTSIDE = [
    {"pk": "a", "pn": "Ann", "okey": "o1", "oname": "Big Bank", "rel": "BOARD_SEAT", "page": 20, "quote": "Ann sits on Big Bank"},
    {"pk": "b", "pn": "Bob", "okey": "o1", "oname": "Big Bank", "rel": "EMPLOYED_BY", "page": 41, "quote": "Bob worked at Big Bank"},
    {"pk": "z", "pn": "Stranger", "okey": "o2", "oname": "Other", "rel": "BOARD_SEAT", "page": 1, "quote": "x"},
]


def test_build_merges_roles_and_finds_interlocks():
    g = build("0000000001", "0000000001-23-000001", ["0000000001-23-000001"], ROLES, COMMITTEES, OUTSIDE, [])
    people = {n["label"]: n for n in g["nodes"] if n["kind"] == "person"}
    assert sorted(people["Bob"]["roles"]) == ["director", "officer"] and people["Bob"]["title"] == "CFO"
    assert "Stranger" not in people                                # not tied to this company
    assert g["counts"]["interlocks"] == 1                          # Ann and Bob share Big Bank
    assert any(e["type"] == "chair" and e["page"] == 12 for e in g["edges"])


def test_api_uses_reader_and_rejects_bad_input():
    app.dependency_overrides[get_graph_reader] = lambda: (
        lambda cik, acc: build(cik, "A-23-1", ["A-23-1"], ROLES, COMMITTEES, OUTSIDE, []))
    try:
        r = client.get("/api/graph/1")
        assert r.status_code == 200 and r.json()["cik"] == "0000000001"
        assert client.get("/api/graph/abc").status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_api_503_when_graph_db_is_down():
    def broken(cik, acc):
        raise RuntimeError("down")
    app.dependency_overrides[get_graph_reader] = lambda: broken
    try:
        assert client.get("/api/graph/1").status_code == 503
    finally:
        app.dependency_overrides.clear()