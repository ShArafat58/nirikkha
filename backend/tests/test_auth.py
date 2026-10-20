import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.auth.deps import get_user_store
from app.auth.security import SECURITY_QUESTIONS
from app.main import app


class Users:
    def __init__(self):
        self.rows, self.requests, self.used = {}, [], {}

    def get_by_email(self, email):
        return next((u for u in self.rows.values() if u["email"] == email), None)

    def get(self, user_id):
        return self.rows.get(user_id)

    def create(self, **fields):
        i = str(uuid.uuid4())
        self.rows[i] = {"id": i, "login_failures": 0, "login_locked_until": None, "reset_failures": 0,
                        "reset_locked_until": None, "created_at": datetime.now(timezone.utc), "last_login_at": None,
                        **fields}
        return self.rows[i]

    def update(self, user_id, **fields):
        self.rows[user_id].update(fields)

    def usage_this_month(self, user_id):
        return self.used.get(user_id, 0)

    def create_plan_request(self, user_id, plan, kind, note):
        self.requests.append((user_id, plan, kind, note))
        return "req-1"


SIGNUP = {"name": "Ayesha Rahman", "email": "Ayesha@Example.com", "password": "Strong1pass",
          "date_of_birth": "1995-05-01", "security_question": SECURITY_QUESTIONS[0],
          "security_answer": "Udayan School", "organization": "Fund X", "job_role": "analyst"}


@pytest.fixture
def api():
    users = Users()
    app.dependency_overrides[get_user_store] = lambda: users
    yield TestClient(app), users
    app.dependency_overrides.clear()


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_signup_then_me(api):
    client, users = api
    r = client.post("/api/auth/signup", json=SIGNUP)
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["email"] == "ayesha@example.com" and body["user"]["role"] == "user"
    assert "password_hash" not in body["user"] and "date_of_birth" not in str(users.rows)
    row = next(iter(users.rows.values()))
    assert row["password_hash"].startswith("$argon2id$") and row["adult_verified"] is True
    me = client.get("/api/auth/me", headers=auth(body["token"])).json()
    assert me["usage"] == {"used_this_month": 0, "limit": 3, "unlimited": False, "remaining": 3}


def test_signup_validation(api):
    client, _ = api
    weak = client.post("/api/auth/signup", json={**SIGNUP, "password": "weakpass"})
    assert weak.status_code == 422 and "upper-case" in weak.json()["detail"] and "number" in weak.json()["detail"]
    young = client.post("/api/auth/signup", json={**SIGNUP, "date_of_birth": "2015-01-01"})
    assert young.status_code == 422 and "at least 18" in young.json()["detail"]
    assert client.post("/api/auth/signup", json={**SIGNUP, "security_question": "My own?"}).status_code == 422
    assert client.post("/api/auth/signup", json={**SIGNUP, "email": "not-an-email"}).status_code == 422
    assert client.post("/api/auth/signup", json=SIGNUP).status_code == 201
    assert client.post("/api/auth/signup", json=SIGNUP).status_code == 409


def test_login_and_lockout(api):
    client, _ = api
    client.post("/api/auth/signup", json=SIGNUP)
    ok = client.post("/api/auth/login", json={"email": " AYESHA@example.com ", "password": "Strong1pass"})
    assert ok.status_code == 200 and ok.json()["token"]
    assert client.post("/api/auth/login", json={"email": "nobody@x.com", "password": "x"}).status_code == 401
    for _ in range(5):
        assert client.post("/api/auth/login", json={"email": SIGNUP["email"], "password": "Wrong1pass"}).status_code == 401
    locked = client.post("/api/auth/login", json={"email": SIGNUP["email"], "password": "Strong1pass"})
    assert locked.status_code == 429 and "Try again in" in locked.json()["detail"]


def test_forgot_and_reset_with_security_question(api):
    client, users = api
    client.post("/api/auth/signup", json=SIGNUP)
    assert client.post("/api/auth/forgot", json={"email": SIGNUP["email"]}).json()["question"] == SECURITY_QUESTIONS[0]
    assert client.post("/api/auth/forgot", json={"email": "nobody@x.com"}).json()["question"] in SECURITY_QUESTIONS
    wrong = client.post("/api/auth/reset", json={"email": SIGNUP["email"], "answer": "Holy Cross", "new_password": "Newer2pass"})
    assert wrong.status_code == 401
    weak = client.post("/api/auth/reset", json={"email": SIGNUP["email"], "answer": "udayan school", "new_password": "weak"})
    assert weak.status_code == 422
    ok = client.post("/api/auth/reset", json={"email": SIGNUP["email"], "answer": " udayan  SCHOOL! ", "new_password": "Newer2pass"})
    assert ok.status_code == 200 and ok.json()["token"]
    assert client.post("/api/auth/login", json={"email": SIGNUP["email"], "password": "Strong1pass"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": SIGNUP["email"], "password": "Newer2pass"}).status_code == 200


def test_reset_lockout(api):
    client, _ = api
    client.post("/api/auth/signup", json=SIGNUP)
    for _ in range(5):
        client.post("/api/auth/reset", json={"email": SIGNUP["email"], "answer": "nope", "new_password": "Newer2pass"})
    r = client.post("/api/auth/reset", json={"email": SIGNUP["email"], "answer": "Udayan School", "new_password": "Newer2pass"})
    assert r.status_code == 429


def test_demo_is_unlimited_and_cannot_password_login(api):
    client, _ = api
    d = client.post("/api/auth/demo").json()
    assert d["user"]["role"] == "demo"
    assert client.post("/api/auth/demo").json()["user"]["id"] == d["user"]["id"]      # one shared demo account
    me = client.get("/api/auth/me", headers=auth(d["token"])).json()
    assert me["usage"]["unlimited"] is True
    assert client.post("/api/auth/login", json={"email": "demo@nirikkha.demo", "password": "x"}).status_code == 401


def test_plans_and_plan_requests(api):
    client, users = api
    plans = client.get("/api/plans").json()
    assert [p["id"] for p in plans["plans"]] == ["free", "analyst_pro", "team", "enterprise"]
    assert client.post("/api/plans/request", json={"plan": "team"}).status_code == 401
    token = client.post("/api/auth/signup", json=SIGNUP).json()["token"]
    assert client.post("/api/plans/request", json={"plan": "gold"}, headers=auth(token)).status_code == 422
    r = client.post("/api/plans/request", json={"plan": "team", "kind": "pilot", "note": "5 analysts"}, headers=auth(token))
    assert r.status_code == 201 and "No payment" in r.json()["message"] and users.requests[0][1:] == ("team", "pilot", "5 analysts")
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer broken"}).status_code == 401