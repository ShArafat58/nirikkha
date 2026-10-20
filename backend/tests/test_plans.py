from app.business.plans import ADD_ONS, PLANS, monthly_limit, projected_mrr


def test_plans_match_the_business_model():
    by_id = {p["id"]: p for p in PLANS}
    assert [p["id"] for p in PLANS] == ["free", "analyst_pro", "team", "enterprise"]
    assert by_id["free"]["crash_tests_per_month"] == 3 and by_id["analyst_pro"]["price_usd"] == 49
    assert by_id["team"]["price_usd"] == 399 and by_id["team"]["crash_tests_per_month"] == 150
    assert by_id["enterprise"]["price_usd"] is None
    assert {a["id"]: a["price_usd"] for a in ADD_ONS} == {"extra_crash_test": 19, "deep_investigation": 199}


def test_demo_and_admin_are_unlimited():
    assert monthly_limit("user", "free") == 3 and monthly_limit("user", "analyst_pro") == 30
    assert monthly_limit("demo", "free") is None and monthly_limit("admin", "free") is None
    assert monthly_limit("user", "enterprise") is None


def test_projected_mrr_matches_the_pdf_example():
    m = projected_mrr({"analyst_pro": 100, "team": 10, "free": 500, "enterprise": 1})
    assert m["total_monthly_usd"] == 8890 and "no live payments" in m["label"]