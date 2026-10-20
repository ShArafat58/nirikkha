import pytest
from fastapi.testclient import TestClient

from app.auth.deps import get_current_user
from app.business.routes import get_billing_store
from app.main import app


class Billing:
    def __init__(self):
        self.records = []

    def subscribe(self, user_id, plan, method, amount_usd, reference):
        rec = {"id": str(len(self.records) + 1), "plan": plan, "method": method, "amount_usd": amount_usd,
               "reference": reference, "status": "succeeded", "created_at": "2026-10-21T00:00:00Z"}
        self.records.append((user_id, rec))
        return rec

    def history(self, user_id):
        return [r for u, r in self.records if u == user_id]


@pytest.fixture
def billing():
    store = Billing()
    user = {"id": "u1", "role": "user", "plan": "free"}
    app.dependency_overrides[get_billing_store] = lambda: store
    app.dependency_overrides[get_current_user] = lambda: user
    yield TestClient(app), store, user
    app.dependency_overrides.clear()


def test_checkout_activates_plan_without_money(billing):
    client, store, _ = billing
    r = client.post("/api/billing/checkout", json={"plan": "team", "method": "mobile_banking"})
    assert r.status_code == 201
    body = r.json()
    assert body["plan"] == "team" and body["amount_usd"] == 399.0 and body["simulated"] is True
    assert body["reference"].startswith("SIM-") and "no money was charged" in body["note"]
    assert client.get("/api/billing/history").json()[0]["reference"] == body["reference"]


def test_checkout_rules(billing):
    client, _, user = billing
    assert client.post("/api/billing/checkout", json={"plan": "enterprise", "method": "card"}).status_code == 422
    assert client.post("/api/billing/checkout", json={"plan": "free", "method": "card"}).status_code == 422
    assert client.post("/api/billing/checkout", json={"plan": "team", "method": "bitcoin"}).status_code == 422
    assert client.post("/api/billing/checkout", json={"plan": "gold", "method": "card"}).status_code == 422
    user["plan"] = "team"
    assert client.post("/api/billing/checkout", json={"plan": "team", "method": "card"}).status_code == 409


def test_no_payment_details_are_accepted(billing):
    client, store, _ = billing
    r = client.post("/api/billing/checkout", json={"plan": "analyst_pro", "method": "card", "card_number": "4111111111111111"})
    assert r.status_code == 201 and "4111" not in str(store.records)


def test_cancel_back_to_free(billing):
    client, _, user = billing
    assert client.post("/api/billing/cancel").status_code == 409
    user["plan"] = "team"
    r = client.post("/api/billing/cancel").json()
    assert r["plan"] == "free" and r["amount_usd"] == 0.0 and r["method"] == "none"