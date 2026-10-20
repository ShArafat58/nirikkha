"""Plans and prices from the business model (plan PDF, section 11). Single source for the pricing page and limits.

Prices are proposed list prices in USD; the prototype has no live payments (plan choices are recorded as requests).
Demo and admin accounts are unlimited so judges and the owner can see every feature.
"""

from __future__ import annotations

PLANS = [
    {"id": "free", "name": "Free", "audience": "Students, individual investors, trials",
     "price_usd": 0, "price_unit": "month", "price_label": "$0",
     "crash_tests_per_month": 3, "radar_companies": 0,
     "features": ["3 Crash-Tests per month", "Summary report", "Evidence links to SEC filings"]},
    {"id": "analyst_pro", "name": "Analyst Pro", "audience": "Individual analysts, small funds",
     "price_usd": 49, "price_unit": "user / month", "price_label": "$49 per user / month",
     "crash_tests_per_month": 30, "radar_companies": 10,
     "features": ["30 Crash-Tests per month", "Full evidence and Rule Engine results", "PDF export",
                  "Regulatory Radar alerts for 10 companies"]},
    {"id": "team", "name": "Team", "audience": "Research and compliance teams (up to 5 users)",
     "price_usd": 399, "price_unit": "month", "price_label": "$399 / month",
     "crash_tests_per_month": 150, "radar_companies": 50,
     "features": ["150 Crash-Tests per month", "Shared workspace", "Decision workflow", "Audit trail",
                  "Regulatory Radar for 50 companies"]},
    {"id": "enterprise", "name": "Enterprise", "audience": "Banks, institutional investors, large compliance teams",
     "price_usd": None, "price_unit": "year", "price_label": "Annual contract",
     "crash_tests_per_month": None, "radar_companies": None,
     "features": ["Approved private documents", "Runs on your own servers (data stays inside)", "Custom rules",
                  "SSO", "Unlimited use"]},
]
ADD_ONS = [
    {"id": "extra_crash_test", "name": "Extra Crash-Test", "price_usd": 19,
     "description": "One more Crash-Test after the plan limit is reached"},
    {"id": "deep_investigation", "name": "Deep Investigation Report", "price_usd": 199,
     "description": "Multi-year filings, cross-document check, Replay-style historical analysis, approval-ready PDF"},
]
PLAN_IDS = {p["id"] for p in PLANS}
UNLIMITED_ROLES = {"demo", "admin"}


def plan(plan_id: str) -> dict:
    return next(p for p in PLANS if p["id"] == plan_id)


def monthly_limit(role: str, plan_id: str) -> int | None:
    """Crash-Tests per month; None = unlimited."""
    if role in UNLIMITED_ROLES:
        return None
    return plan(plan_id)["crash_tests_per_month"]


def projected_mrr(users_by_plan: dict[str, int]) -> dict:
    """Projected monthly revenue at list price (no live payments). Enterprise is a contract, reported separately."""
    lines, total = [], 0
    for p in PLANS:
        n = users_by_plan.get(p["id"], 0)
        if p["price_usd"] is None:
            lines.append({"plan": p["id"], "accounts": n, "monthly_usd": None, "note": "annual contract"})
            continue
        amount = n * p["price_usd"]
        total += amount
        lines.append({"plan": p["id"], "accounts": n, "monthly_usd": amount})
    return {"total_monthly_usd": total, "lines": lines,
            "label": "Projected revenue at list price - no live payments in the prototype"}