from datetime import date

from app.auth.security import (
    SECURITY_QUESTIONS, auth_secret, check_birth_date, create_token, decoy_question, hash_secret,
    normalize_answer, password_problems, read_token, verify_secret,
)


def test_password_policy():
    assert password_problems("Strong1pass") == []
    assert set(password_problems("weak")) == {"At least 8 characters", "An upper-case letter (A-Z)", "A number (0-9)"}
    assert password_problems("ALLUPPER123") == ["A lower-case letter (a-z)"]
    assert "At most 128 characters" in password_problems("Aa1" + "x" * 200)


def test_hashes_never_equal_plain_text_and_verify():
    h = hash_secret("Strong1pass")
    assert "Strong1pass" not in h and h.startswith("$argon2id$")
    assert verify_secret(h, "Strong1pass") and not verify_secret(h, "strong1pass")
    assert not verify_secret("not-a-hash", "x")


def test_security_answers_ignore_case_space_and_punctuation():
    stored = hash_secret(normalize_answer("Viqarunnisa Noon School"))
    assert verify_secret(stored, normalize_answer("  viqarunnisa   noon school! "))
    assert not verify_secret(stored, normalize_answer("Holy Cross"))


def test_birth_date_checks_18_plus():
    today = date(2026, 10, 20)
    assert check_birth_date(date(2008, 10, 20), today) is None          # exactly 18 today
    assert "at least 18" in check_birth_date(date(2008, 10, 21), today)
    assert "future" in check_birth_date(date(2027, 1, 1), today)
    assert check_birth_date(date(1890, 1, 1), today) == "Please check the date of birth."


def test_tokens_round_trip_and_expire():
    t = create_token("u1", "user", "test-secret-key-that-is-at-least-32-bytes", ttl=60, now=1_000_000)
    assert read_token(t, "another-secret-key-that-is-32-bytes-long") is None
    t2 = create_token("u1", "admin", "test-secret-key-that-is-at-least-32-bytes", ttl=3600)
    assert read_token(t2, "test-secret-key-that-is-at-least-32-bytes")["role"] == "admin"
    assert read_token(t, "test-secret-key-that-is-at-least-32-bytes") is None                                # expired long ago


def test_production_needs_a_secret_and_decoy_is_stable():
    assert auth_secret("x" * 32, "production") == "x" * 32
    try:
        auth_secret("", "production")
        assert False
    except RuntimeError:
        pass
    assert decoy_question("nobody@x.com") == decoy_question("NOBODY@x.com ") in SECURITY_QUESTIONS