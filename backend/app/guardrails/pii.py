"""PII redaction guardrail: personal data in user-written text is masked before any model sees it.

Applied to the decision text (and later to uploads). Public SEC filing text is NOT redacted: the names of
directors and officers in a filing are the evidence. Only counts per type are kept, never the original values.

False-positive controls: card numbers must pass the Luhn check, phone numbers need 9-15 digits, and SEC
accession numbers, CIK numbers and ISO dates are protected.
"""

from __future__ import annotations

import re

PROTECTED = re.compile(r"(?<!\d)\d{10}-\d{2}-\d{6}(?!\d)|(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)|\bCIK\s*#?:?\s*\d{1,10}\b|(?<!\d)000\d{7}(?!\d)")
PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")),
    ("SSN", re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")),
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,7}(?:\s?[A-Z0-9]{1,3})?\b")),
    ("CARD", re.compile(r"(?<![\d-])(?:\d[ -]?){12,18}\d(?![\d-])")),
    ("IP", re.compile(r"(?<!\d)(?<!\d\.)(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?!\d|\.\d)")),
    ("PHONE", re.compile(r"(?<![\w+])\+?\(?\d[\d\s().-]{7,}\d(?!\w)")),
]


def luhn_ok(digits: str) -> bool:
    total, double = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if double:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
        double = not double
    return total % 10 == 0


def _accept(label: str, value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if label == "CARD":
        return 13 <= len(digits) <= 19 and luhn_ok(digits)
    if label == "PHONE":
        return 9 <= len(digits) <= 15
    return True


def redact_pii(text: str) -> tuple[str, dict[str, int]]:
    """Returns (redacted text, counts by type)."""
    if not text:
        return text, {}
    protected = [m.span() for m in PROTECTED.finditer(text)]
    counts: dict[str, int] = {}
    for label, pattern in PATTERNS:
        def sub(m: re.Match) -> str:
            start, end = m.span()
            if any(start < pe and ps < end for ps, pe in protected) or not _accept(label, m.group(0)):
                return m.group(0)
            counts[label] = counts.get(label, 0) + 1
            return f"[{label}]"
        text = pattern.sub(sub, text)
        protected = [m.span() for m in PROTECTED.finditer(text)]
    return text, counts