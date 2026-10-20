import pytest
from fastapi.testclient import TestClient

from app.admin.routes import get_admin_store
from app.auth.admin import create_or_promote
from app.auth.deps import get_current_user
from app.main import app


class Admin:
    def __init__(self):
        self.plans, self.statuses, self.reviews = {}, {}, []

    def overview(self):
        return {"accounts": [{"role": "user", "plan": "analyst_pro", "n": 100}, {"role": "user", "plan": "team", "n": 10},
                             {"role": "user", "plan": "free", "n": 40}, {"role": "demo", "plan": "free", "n": 1}],
                "signups": {"users": 150, "last_30_days": 12}, "crash_tests_by_status": [{"status": "done", "n": 5}],
                "crash_tests_this_month": 5, "open_plan_requests": 2,
                "model_usage": [{"model": "openai/gpt-oss-120b", "node": "sentinel", "calls": 7}],
                "per_crash_test": {"n": 5, "avg_tokens": 9000, "avg_llm_calls": 5.0, "avg_seconds": 180, "cost_usd": 0.0}}

    def users(self):
        return [{"id": "u1", "email": "a@x.com", "plan": "free", "used_this_month": 2}]

    def set_plan(self, user_id, plan):
        self.plans[user_id] = plan
        return user_id == "u1"

    def plan_requests(self):
        return []

    def set_request_status(self, request_id, status):
        self.statuses[request_id] = status
        return True

    def jobs(self):
        return []

    def review_queue(self):
        return [{"crash_test_id": "c1", "finding_id": "MIS-1", "review": None}]

    def add_review(self, crash_test_id, finding_id, decision, note, reviewer_id):
        if finding_id != "MIS-1":
            return None
        self.reviews.append((crash_test_id, finding_id, decision, note, reviewer_id))
        return "rev-1"


@pytest.fixture
def admin_client():
    store = Admin()
    app.dependency_overrides[get_admin_store] = lambda: store
    app.dependency_overrides[get_current_user] = lambda: {"id": "admin-1", "role": "admin", "plan": "enterprise"}
    yield TestClient(app), store
    app.dependency_overrides.clear()


def test_only_admins(admin_client):
    client, _ = admin_client
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "demo", "plan": "free"}
    assert client.get("/api/admin/overview").status_code == 403


def test_overview_has_labelled_projection_and_unit_economics(admin_client):
    client, _ = admin_client
    o = client.get("/api/admin/overview").json()
    assert o["users_by_plan"] == {"analyst_pro": 100, "team": 10, "free": 40}
    assert o["projected_revenue"]["total_monthly_usd"] == 8890 and "no live payments" in o["projected_revenue"]["label"]
    rev = {r["plan"]: r["revenue_per_crash_test_usd"] for r in o["unit_economics"]["revenue_per_crash_test"]}
    assert rev == {"analyst_pro": 1.63, "team": 2.66}
    assert o["unit_economics"]["measured"]["avg_tokens"] == 9000 and "free tiers" in o["unit_economics"]["note"]


def test_set_plan_and_request_status(admin_client):
    client, store = admin_client
    assert client.post("/api/admin/users/u1/plan", json={"plan": "team"}).json() == {"id": "u1", "plan": "team"}
    assert client.post("/api/admin/users/u1/plan", json={"plan": "gold"}).status_code == 422
    assert client.post("/api/admin/users/u9/plan", json={"plan": "team"}).status_code == 404
    assert client.post("/api/admin/plan-requests/r1", json={"status": "contacted"}).status_code == 200
    assert client.post("/api/admin/plan-requests/r1", json={"status": "paid"}).status_code == 422


def test_review_queue_and_audit_trail(admin_client):
    client, store = admin_client
    assert client.get("/api/admin/reviews").json()[0]["finding_id"] == "MIS-1"
    r = client.post("/api/admin/reviews", json={"crash_test_id": "c1", "finding_id": "MIS-1", "decision": "reject",
                                                "note": "Absence claim: the 10-K does disclose liquidity metrics."})
    assert r.status_code == 201 and store.reviews[0][2:] == ("reject", "Absence claim: the 10-K does disclose liquidity metrics.", "admin-1")
    assert client.post("/api/admin/reviews", json={"crash_test_id": "c1", "finding_id": "XX-9", "decision": "approve"}).status_code == 404
    assert client.post("/api/admin/reviews", json={"crash_test_id": "c1", "finding_id": "MIS-1", "decision": "maybe"}).status_code == 422


def test_admin_cli_helper():
    class Users:
        def __init__(self):
            self.rows = {}

        def get_by_email(self, email):
            return self.rows.get(email)

        def create(self, **f):
            self.rows[f["email"]] = {"id": "1", **f}

        def update(self, user_id, **f):
            next(iter(self.rows.values())).update(f)

    users = Users()
    assert create_or_promote(users, "Boss@X.com", "Boss", "Strong1pass", "Q?", "A") == "created admin boss@x.com"
    assert users.rows["boss@x.com"]["role"] == "admin" and users.rows["boss@x.com"]["password_hash"].startswith("$argon2id$")
    users.rows["boss@x.com"]["role"] = "user"
    assert create_or_promote(users, "boss@x.com", "Boss", "", "", "") == "promoted boss@x.com to admin"
    try:
        create_or_promote(Users(), "y@x.com", "Y", "weak", "Q?", "A")
        assert False
    except ValueError as exc:
        assert "upper-case" in str(exc)