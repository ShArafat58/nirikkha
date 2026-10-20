"""Create an admin account, or promote an existing account to admin (run on a trusted machine).

    python -m app.auth.admin --email you@example.com --name "Your Name"
"""

from __future__ import annotations

import argparse
import getpass
import sys
from typing import Any

from app.auth.security import SECURITY_QUESTIONS, hash_secret, normalize_answer, password_problems


def create_or_promote(users: Any, email: str, name: str, password: str, question: str, answer: str) -> str:
    email = email.strip().lower()
    existing = users.get_by_email(email)
    if existing:
        users.update(existing["id"], role="admin")
        return f"promoted {email} to admin"
    problems = password_problems(password)
    if problems:
        raise ValueError("Password needs: " + "; ".join(problems))
    users.create(email=email, name=name, organization=None, job_role="Administrator",
                 password_hash=hash_secret(password), security_question=question,
                 security_answer_hash=hash_secret(normalize_answer(answer)), role="admin", plan="enterprise",
                 adult_verified=True)
    return f"created admin {email}"


def _main(argv: list[str]) -> int:
    from app.auth.store import PostgresUserStore

    parser = argparse.ArgumentParser(description="Create or promote an admin account")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args(argv[1:])
    users = PostgresUserStore()
    if users.get_by_email(args.email.strip().lower()):
        print(create_or_promote(users, args.email, args.name, "", "", ""))
        return 0
    password = getpass.getpass("Password (8+ chars, upper, lower, number): ")
    if getpass.getpass("Repeat password: ") != password:
        print("Passwords do not match.")
        return 1
    problems = password_problems(password)
    if problems:
        print("ERROR: Password needs: " + "; ".join(problems))
        return 1
    for i, q in enumerate(SECURITY_QUESTIONS, 1):
        print(f"  {i}. {q}")
    choice = int(input("Security question number: ").strip())
    answer = getpass.getpass("Answer (hidden): ")
    try:
        print(create_or_promote(users, args.email, args.name, password, SECURITY_QUESTIONS[choice - 1], answer))
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))