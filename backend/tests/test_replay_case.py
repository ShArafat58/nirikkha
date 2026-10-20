import copy

import pytest

from app.replay.case import (
    CaseError, evidence_window, frozen_events, is_knowable, load_case, validate, visible_events,
)


@pytest.fixture
def svb():
    return load_case("svb")


def test_svb_case_is_valid(svb):
    assert svb["freeze_date"] == "2023-03-07"
    assert svb["freeze_date"] < svb["outcome_date"]


def test_freeze_hides_crisis_news(svb):
    visible = {e["id"] for e in visible_events(svb)}
    frozen = {e["id"] for e in frozen_events(svb)}
    assert {"ev_10k_fy2022", "ev_def14a_2022", "ev_pre14a_2023"} <= visible
    assert {"ev_8k_afs_sale", "ev_run", "ev_failure", "ev_barr_review"} <= frozen


def test_visibility_uses_public_date_not_event_date(svb):
    ev = next(e for e in svb["timeline"] if e["id"] == "ev_fed_irr_finding")
    assert ev["event_date"] < svb["freeze_date"] < ev["public_date"]
    assert "ev_fed_irr_finding" not in {e["id"] for e in visible_events(svb)}


def test_hindsight_guard_rejects_post_freeze_evidence(svb):
    case = copy.deepcopy(svb)
    case["warning_signs"][0]["pre_freeze_evidence"].append("ev_barr_review")
    with pytest.raises(CaseError, match="hindsight"):
        validate(case)


def test_case_admits_what_could_not_be_known(svb):
    unknowable = [s["id"] for s in svb["warning_signs"] if not is_knowable(s)]
    assert unknowable == ["ws_supervisory_findings"]


def test_evidence_window_splits_filings(svb):
    filings = [
        {"form": "10-K", "filing_date": "2023-02-24"},
        {"form": "8-K", "filing_date": "2023-03-08"},
    ]
    allowed, excluded = evidence_window(svb, filings)
    assert [f["form"] for f in allowed] == ["10-K"]
    assert [f["form"] for f in excluded] == ["8-K"]


def test_source_must_be_https(svb):
    case = copy.deepcopy(svb)
    case["timeline"][0]["sources"][0]["url"] = "http://example.com"
    with pytest.raises(CaseError, match="https"):
        validate(case)


def test_unknown_case():
    with pytest.raises(CaseError, match="not found"):
        load_case("no-such-case")