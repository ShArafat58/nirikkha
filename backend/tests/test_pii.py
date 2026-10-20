from app.guardrails.pii import luhn_ok, redact_pii


def test_redacts_common_personal_data():
    text = ("Contact jane.doe@example.com or +880 1712-345678 or (415) 555-0132. SSN 123-45-6789, "
            "card 4111 1111 1111 1111, IBAN GB82 WEST 1234 5698 7654 32, from 192.168.1.20.")
    out, counts = redact_pii(text)
    assert "example.com" not in out and "1712" not in out and "555-0132" not in out
    assert "6789" not in out and "4111" not in out and "WEST" not in out and "192.168" not in out
    assert counts == {"EMAIL": 1, "SSN": 1, "IBAN": 1, "CARD": 1, "IP": 1, "PHONE": 2}


def test_keeps_public_filing_references_and_amounts():
    text = ("Filing 0001193125-22-064940 dated 2022-03-04, CIK 0000719739, fees of $706,674 and $30.0 million, "
            "threshold $120,000, fiscal 2022 and 2023, Mr. Becker of SVB Financial Group.")
    out, counts = redact_pii(text)
    assert out == text and counts == {}


def test_card_needs_luhn():
    assert luhn_ok("4111111111111111") and not luhn_ok("4111111111111112")
    out, counts = redact_pii("ref 4111 1111 1111 1112")
    assert "CARD" not in counts


def test_empty_text():
    assert redact_pii("") == ("", {})