"""Password, security-answer and token primitives.

- Passwords and security answers: argon2id (argon2-cffi defaults), never stored in plain text.
- Password policy: 8-128 characters with an upper-case letter, a lower-case letter and a digit.
- Security questions come from a fixed list; answers are compared case-, space- and punctuation-insensitively.
- Age: the date of birth is only used to check 18+; it is never stored.
- Tokens: HS256 JWT signed with AUTH_SECRET (required in production).
"""

from __future__ import annotations

import hashlib
import re
import secrets
import time
from datetime import date

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

SECURITY_QUESTIONS = [
    "What was the name of your first school?",
    "In which city were you born?",
    "What was the name of your first pet?",
    "What is the title of your favourite book?",
    "What was the model of your first mobile phone?",
]
PASSWORD_RULES = [
    ("min_length", "At least 8 characters", lambda p: len(p) >= 8),
    ("upper", "An upper-case letter (A-Z)", lambda p: re.search(r"[A-Z]", p) is not None),
    ("lower", "A lower-case letter (a-z)", lambda p: re.search(r"[a-z]", p) is not None),
    ("digit", "A number (0-9)", lambda p: re.search(r"\d", p) is not None),
]
MAX_PASSWORD = 128
MIN_AGE = 18
MAX_AGE = 120
TOKEN_TTL_SECONDS = 12 * 3600

_hasher = PasswordHasher()
_dev_secret = secrets.token_urlsafe(32)


def password_problems(password: str) -> list[str]:
    problems = [message for _, message, ok in PASSWORD_RULES if not ok(password)]
    if len(password) > MAX_PASSWORD:
        problems.append(f"At most {MAX_PASSWORD} characters")
    return problems


def hash_secret(value: str) -> str:
    return _hasher.hash(value)


def verify_secret(stored_hash: str, value: str) -> bool:
    try:
        return _hasher.verify(stored_hash, value)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def normalize_answer(answer: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", answer.lower()).split())


def age_on(dob: date, today: date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def check_birth_date(dob: date, today: date | None = None) -> str | None:
    """None if the person is 18+, otherwise the reason."""
    today = today or date.today()
    if dob > today:
        return "Date of birth cannot be in the future."
    age = age_on(dob, today)
    if age > MAX_AGE:
        return "Please check the date of birth."
    if age < MIN_AGE:
        return f"You must be at least {MIN_AGE} years old to create an account."
    return None


def auth_secret(configured: str, app_env: str) -> str:
    if configured:
        if app_env == "production" and len(configured) < 32:
            raise RuntimeError("AUTH_SECRET must be at least 32 characters in production.")
        return configured
    if app_env == "production":
        raise RuntimeError("AUTH_SECRET must be set in production.")
    return _dev_secret   # development only: tokens stop working when the process restarts


def create_token(user_id: str, role: str, secret: str, ttl: int = TOKEN_TTL_SECONDS, now: int | None = None,
                 extra: dict | None = None) -> str:
    issued = int(now if now is not None else time.time())
    payload = {"sub": user_id, "role": role, "iat": issued, "exp": issued + ttl, **(extra or {})}
    return jwt.encode(payload, secret, algorithm="HS256")


def read_token(token: str, secret: str) -> dict | None:
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


def decoy_question(email: str) -> str:
    """Stable question for unknown emails, so the reset form does not reveal which emails have accounts."""
    return SECURITY_QUESTIONS[hashlib.sha256(email.strip().lower().encode()).digest()[0] % len(SECURITY_QUESTIONS)]