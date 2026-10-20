"""Entity resolution for extracted governance relations (pure functions, no database).

- People: "MARY MILLER" = "Mary Miller"; "Ms. Burr" = "Elizabeth \"Busy\" Burr" = "Elizabeth Busy Burr".
  Key = first + last name; a bare surname is matched to the unique full name with that surname.
  Multi-person phrases ("Messrs. Daniels and Staglin") are skipped.
- Organizations: "Financial Engines, Inc." = "Financial Engines" (suffixes and punctuation ignored).
- Targets: the filing company -> Company; "... Committee" of the company -> Committee;
  "Committee of <other org>" -> outside Organization; "Board Chair" -> chair of the board;
  anything else -> outside Organization. Only verified relations are kept.
- Evidence from table rows is flagged from_table=True: the row exists, but which column a mark
  belongs to is the model's reading, so the Reliability Sentinel gives it lower confidence.
"""

from __future__ import annotations

import re

from app.graph.extract import normalize_name

_SUFFIX = re.compile(r"\b(incorporated|inc|llc|corporation|corp|limited|ltd|company|co|plc|lp|the)\b\.?", re.I)
_NICKNAME = re.compile(r"[\u201c\u201d\"].*?[\u201c\u201d\"]")
_BOARD_CHAIR = re.compile(
    r"^(board( of directors)?( chair(man|person)?)?|chair(man|person)? of (the )?board( of directors)?)$"
)
_MULTI_PERSON = re.compile(r"\b(and|messrs|mses|mmes)\b", re.I)
_OUTSIDE_COMMITTEE = re.compile(r"\bcommittee of (.+)$", re.I)


def org_key(name: str) -> str:
    s = name.lower().replace("&", " and ")
    s = re.sub(r"[\u201c\u201d\"'\u2019().,]", " ", s)
    s = _SUFFIX.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def person_tokens(name: str) -> list[str]:
    n = _NICKNAME.sub(" ", normalize_name(name))
    n = re.sub(r"[^A-Za-z\- ]", " ", n).lower()
    return [t for t in n.split() if t not in {"jr", "sr", "ii", "iii", "iv"}]


def person_key(name: str) -> str:
    tokens = person_tokens(name)
    if len(tokens) >= 2:
        return f"{tokens[0]} {tokens[-1]}"
    return tokens[0] if tokens else ""


def is_multi_person(name: str) -> bool:
    return bool(_MULTI_PERSON.search(name))


def is_filer(org: str, company: str) -> bool:
    a, b = org_key(org), org_key(company)
    if not a:
        return False
    return a == b or (len(a) >= 4 and (b.startswith(a) or a.startswith(b))) or a in {"company", "the company"}


def is_board_chair(org: str) -> bool:
    return bool(_BOARD_CHAIR.match(org_key(org)))


def is_committee(org: str) -> bool:
    return "committee" in org.lower()


def outside_committee_owner(org: str, company: str) -> str | None:
    """'Investment Committee of Waterman Ventures' -> 'Waterman Ventures' (if not the filer)."""
    match = _OUTSIDE_COMMITTEE.search(org)
    if match and not is_filer(match.group(1), company):
        return match.group(1).strip()
    return None


def display_name(variants: list[str]) -> str:
    """Prefer a mixed-case variant (as written in prose), longest first; else title-case."""
    cleaned = [re.sub(r"\s+", " ", normalize_name(v)) for v in variants if v.strip()]
    mixed = [v for v in cleaned if not v.isupper()]
    if mixed:
        return max(mixed, key=len)
    return max(cleaned, key=len).title() if cleaned else ""


def resolve_people(names: list[str]) -> dict[str, str]:
    """Map each raw name to a person key, attaching bare surnames to a unique full name."""
    full_by_last: dict[str, set[str]] = {}
    for n in names:
        key = person_key(n)
        if " " in key:
            full_by_last.setdefault(key.split()[-1], set()).add(key)
    mapping: dict[str, str] = {}
    for n in names:
        key = person_key(n)
        if key and " " not in key and len(full_by_last.get(key, set())) == 1:
            key = next(iter(full_by_last[key]))
        mapping[n] = key
    return mapping


def build_rows(extracted: dict) -> list[dict]:
    """Turn an extraction file into graph rows: one row per verified, resolved relationship."""
    company, cik = extracted["company"], extracted["cik"]
    relations = [
        r for r in extracted["relations"]
        if r.get("verified") and (r["relation"] == "RELATED_TRANSACTION" or not is_multi_person(r["person"]))
    ]
    people = resolve_people([r["person"] for r in relations])

    variants: dict[str, list[str]] = {}
    for r in relations:
        variants.setdefault(people[r["person"]], []).append(r["person"])
    names = {k: display_name(v) for k, v in variants.items()}

    rows: list[dict] = []
    for r in relations:
        pkey = people[r["person"]]
        if not pkey:
            continue
        org, rel = r["organization"], r["relation"]
        filer = is_filer(org, company)
        if rel == "DIRECTOR_OF":
            kind = "DIRECTOR_OF" if filer else "BOARD_SEAT"
        elif rel == "OFFICER_OF":
            kind = "OFFICER_OF" if filer else "EMPLOYED_BY"
        elif rel in ("COMMITTEE_CHAIR", "COMMITTEE_MEMBER"):
            if is_board_chair(org) and rel == "COMMITTEE_CHAIR":
                kind = "CHAIRS_BOARD"
            elif is_committee(org) and outside_committee_owner(org, company):
                kind = "BOARD_SEAT"  # a committee of another organization
            elif is_committee(org):
                kind = "MEMBER_OF"
            else:
                continue  # not a committee of the company: skip rather than guess
        elif rel == "BOARD_SEAT_ELSEWHERE":
            kind = "DIRECTOR_OF" if filer else "BOARD_SEAT"
        elif rel == "EMPLOYED_BY":
            if filer:
                continue  # employment at the filer itself is covered by OFFICER_OF
            kind = "EMPLOYED_BY"
        elif rel == "RELATED_TRANSACTION":
            kind = "RELATED_TRANSACTION"
        else:
            continue
        rows.append({
            "kind": kind,
            "person_key": pkey,
            "person_name": names.get(pkey, r["person"]),
            "org_key": f"{cik}:{org_key(org)}" if kind == "MEMBER_OF" else org_key(org),
            "org_name": org.strip(),
            "chair": rel == "COMMITTEE_CHAIR",
            "props": {
                "accession_no": r["accession_no"], "chunk_id": r["chunk_id"], "page": r["page_start"],
                "section": r["section_title"], "quote": r["quote"], "title": r.get("title"),
                "independent": r.get("independent"), "amount": r.get("amount"),
                "from_table": "|" in r["quote"],
            },
        })
    return rows