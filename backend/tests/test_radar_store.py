from app.radar.store import InMemoryRadarStore, mask_email


def alert(key, priority="low", event_date="2024-01-01", cik="1"):
    return {"key": key, "stream": "regulatory", "cik": cik, "company": "Co", "title": key,
            "priority": priority, "event_date": event_date, "evidence": {"status": "gap", "passage": None}}


def test_rescan_keeps_the_human_decision():
    s = InMemoryRadarStore()
    s.upsert([alert("a", "high")])
    a = s.list()[0]
    s.decide(a["id"], "approve", "checked with legal", "u1", "analyst@example.com")
    s.upsert([alert("a", "high", event_date="2024-02-01")])      # same alert seen again
    again = s.get(a["id"])
    assert again["status"] == "approved" and again["event_date"] == "2024-02-01"
    assert again["decided_by_email"] == "a***@example.com"


def test_every_decision_is_kept_in_order():
    s = InMemoryRadarStore()
    s.upsert([alert("a")])
    a_id = s.list()[0]["id"]
    s.decide(a_id, "reject", "not material", "u1", "x@y.org")
    s.decide(a_id, "approve", "new evidence", "u2", "z@y.org")
    assert [h["decision"] for h in s.history(a_id)] == ["rejected", "approved"]
    assert s.get(a_id)["status"] == "approved"


def test_list_orders_by_priority_then_newest():
    s = InMemoryRadarStore()
    s.upsert([alert("low-new", "low", "2025-01-01"), alert("high-old", "high", "2020-01-01"),
              alert("high-new", "high", "2024-01-01")])
    assert [a["key"] for a in s.list()] == ["high-new", "high-old", "low-new"]


def test_unknown_alert_and_masking():
    s = InMemoryRadarStore()
    assert s.decide("nope", "approve", None, None, None) is None
    assert mask_email("bad") is None