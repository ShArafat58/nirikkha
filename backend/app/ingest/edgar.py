"""SEC EDGAR client: find a company's 10-K and DEF 14A filings and download them.

SEC fair-access rules: send a descriptive User-Agent (name + email) and stay
well under 10 requests per second. We cap at about 5 requests per second.

Run directly to try it:
    python -m app.ingest.edgar AAPL
    python -m app.ingest.edgar 719739 --before 2023-03-10
"""

from __future__ import annotations

import hashlib
import json
import sys
import threading
import time
from datetime import date
from pathlib import Path
from typing import Iterable

import httpx
from pydantic import BaseModel

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SUBMISSIONS_EXTRA_URL = "https://data.sec.gov/submissions/{name}"
ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/{doc}"

DEFAULT_FORMS = ("10-K", "DEF 14A")
METADATA_TTL_SECONDS = 24 * 3600
RETRY_STATUS = {403, 429, 500, 502, 503, 504}


class EdgarError(RuntimeError):
    """Raised with a clear, user-facing message when EDGAR access fails."""


class FilingRef(BaseModel):
    cik: str
    company: str
    form: str
    accession_no: str
    filing_date: date
    report_date: date | None = None
    primary_document: str
    url: str


def normalize_cik(value: str | int) -> str:
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if not digits or len(digits) > 10:
        raise EdgarError(f"Invalid CIK: {value!r}")
    return digits.zfill(10)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


class EdgarClient:
    def __init__(
        self,
        user_agent: str,
        cache_dir: Path | None = None,
        min_interval: float = 0.2,
        transport: httpx.BaseTransport | None = None,
        max_retries: int = 3,
    ) -> None:
        if not user_agent or "@" not in user_agent or "example.com" in user_agent:
            raise EdgarError("SEC_USER_AGENT must contain a real name and email (SEC requirement).")
        self._client = httpx.Client(
            headers={"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"},
            timeout=30.0,
            follow_redirects=True,
            transport=transport,
        )
        self._cache_dir = cache_dir
        self._min_interval = min_interval
        self._max_retries = max_retries
        self._lock = threading.Lock()
        self._last_request = 0.0

    # ---------- lifecycle ----------
    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "EdgarClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---------- low-level HTTP with cache, throttle, retry ----------
    def _cache_path(self, url: str) -> Path | None:
        if self._cache_dir is None:
            return None
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self._cache_dir / "edgar" / key

    def _throttle(self) -> None:
        with self._lock:
            wait = self._min_interval - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
            self._last_request = time.monotonic()

    def _get(self, url: str, ttl: float | None = None) -> bytes:
        """GET with disk cache. ttl=None means cache forever (EDGAR archives never change)."""
        path = self._cache_path(url)
        if path is not None and path.exists():
            age = time.time() - path.stat().st_mtime
            if ttl is None or age < ttl:
                return path.read_bytes()

        last_error = "unknown error"
        for attempt in range(self._max_retries):
            self._throttle()
            try:
                resp = self._client.get(url)
            except httpx.HTTPError as exc:
                last_error = f"network error: {exc}"
            else:
                if resp.status_code == 200:
                    if path is not None:
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_bytes(resp.content)
                    return resp.content
                if resp.status_code == 404:
                    raise EdgarError(f"Not found on EDGAR: {url}")
                last_error = f"HTTP {resp.status_code}"
                if resp.status_code not in RETRY_STATUS:
                    break
            time.sleep(min(2**attempt, 8))
        raise EdgarError(f"EDGAR request failed ({last_error}): {url}")

    def _get_json(self, url: str, ttl: float | None = None) -> dict:
        try:
            return json.loads(self._get(url, ttl=ttl))
        except json.JSONDecodeError as exc:
            raise EdgarError(f"EDGAR returned invalid JSON: {url}") from exc

    # ---------- public API ----------
    def lookup_company(self, ticker_or_cik: str) -> tuple[str, str]:
        """Return (10-digit CIK, company name) for a ticker or a CIK."""
        value = ticker_or_cik.strip()
        if value.isdigit():
            cik = normalize_cik(value)
            data = self._get_json(SUBMISSIONS_URL.format(cik=cik), ttl=METADATA_TTL_SECONDS)
            return cik, data.get("name", "")
        tickers = self._get_json(TICKERS_URL, ttl=METADATA_TTL_SECONDS)
        wanted = value.upper()
        for row in tickers.values():
            if str(row.get("ticker", "")).upper() == wanted:
                return normalize_cik(row["cik_str"]), row.get("title", "")
        raise EdgarError(f"Ticker not found on EDGAR: {value}. Try the company's CIK instead.")

    def list_filings(
        self,
        cik: str | int,
        forms: Iterable[str] = DEFAULT_FORMS,
        before: date | None = None,
        per_form: int = 2,
    ) -> list[FilingRef]:
        """Latest filings of the given forms, newest first.

        before: only filings filed strictly before this date (used to freeze evidence for the Replay).
        """
        cik = normalize_cik(cik)
        wanted = set(forms)
        data = self._get_json(SUBMISSIONS_URL.format(cik=cik), ttl=METADATA_TTL_SECONDS)
        company = data.get("name", "")
        filings = data.get("filings", {})

        refs = self._collect(cik, company, filings.get("recent", {}), wanted, before)

        # Older filings live in extra JSON files; read them only while still short.
        for extra in filings.get("files", []):
            if all(sum(1 for r in refs if r.form == f) >= per_form for f in wanted):
                break
            name = extra.get("name")
            if not name:
                continue
            block = self._get_json(SUBMISSIONS_EXTRA_URL.format(name=name), ttl=METADATA_TTL_SECONDS)
            refs.extend(self._collect(cik, company, block, wanted, before))

        unique = {r.accession_no: r for r in refs}
        ordered = sorted(unique.values(), key=lambda r: r.filing_date, reverse=True)
        counts: dict[str, int] = {}
        result: list[FilingRef] = []
        for ref in ordered:
            if counts.get(ref.form, 0) < per_form:
                result.append(ref)
                counts[ref.form] = counts.get(ref.form, 0) + 1
        return result

    @staticmethod
    def _collect(cik: str, company: str, block: dict, wanted: set[str], before: date | None) -> list[FilingRef]:
        forms = block.get("form", [])
        accessions = block.get("accessionNumber", [])
        filing_dates = block.get("filingDate", [])
        report_dates = block.get("reportDate", [])
        documents = block.get("primaryDocument", [])
        refs: list[FilingRef] = []
        for i, form in enumerate(forms):
            if form not in wanted:
                continue
            filed = _parse_date(filing_dates[i] if i < len(filing_dates) else None)
            if filed is None or (before is not None and filed >= before):
                continue
            doc = documents[i] if i < len(documents) else ""
            if not doc or i >= len(accessions):
                continue
            accession = accessions[i]
            refs.append(
                FilingRef(
                    cik=cik,
                    company=company,
                    form=form,
                    accession_no=accession,
                    filing_date=filed,
                    report_date=_parse_date(report_dates[i] if i < len(report_dates) else None),
                    primary_document=doc,
                    url=ARCHIVE_URL.format(cik_int=int(cik), acc_nodash=accession.replace("-", ""), doc=doc),
                )
            )
        return refs

    def fetch_document(self, ref: FilingRef) -> str:
        """Download the filing's primary document (HTML) as text. Cached forever."""
        raw = self._get(ref.url)
        for encoding in ("utf-8", "cp1252"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")


def _main(argv: list[str]) -> int:
    from app.config import get_settings

    if len(argv) < 2:
        print("usage: python -m app.ingest.edgar <TICKER|CIK> [--before YYYY-MM-DD]")
        return 2
    before = None
    if "--before" in argv:
        before = date.fromisoformat(argv[argv.index("--before") + 1])

    settings = get_settings()
    try:
        with EdgarClient(settings.sec_user_agent, cache_dir=settings.cache_dir) as client:
            cik, name = client.lookup_company(argv[1])
            print(f"{name} (CIK {cik})")
            refs = client.list_filings(cik, before=before)
            for r in refs:
                print(f"  {r.form:8} filed {r.filing_date}  period {r.report_date}  {r.accession_no}")
                print(f"           {r.url}")
            if refs:
                text = client.fetch_document(refs[0])
                print(f"Downloaded {refs[0].form} {refs[0].accession_no}: {len(text):,} characters")
    except EdgarError as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))