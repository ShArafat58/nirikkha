"""Nirikkha Guide - Product Help Chatbot API.

Answers questions about Nirikkha, features, results, pricing, and troubleshooting
using ONLY the curated public knowledge base in docs/HELP_KB.md.

Hard constraints:
- NO database access, NO auth store, NO user data, NO admin data.
- Input and output PII redaction.
- Prompt-injection defenses and admin query defenses.
- Character length (1000) and conversation history limits (6 turns).
- In-memory IP rate limiting (20 requests per 10 minutes).
- Fallback to keyword-matched FAQ if LLM fails.
- Token, latency, and cost logging via the LLM client.
"""

from __future__ import annotations

import re
import time
from collections import deque
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.guardrails.pii import redact_pii
from app.llm.client import LLMError, get_llm

router = APIRouter(prefix="/api/help")

# Paths
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND_DIR.parent
_KB_PATH = _REPO_ROOT / "docs" / "HELP_KB.md"
_PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "help_guide_v2.md"


# Safety regex patterns
_INJECTION_RE = re.compile(
    r"ignore (all |any )?(previous|prior|above) instructions|system prompt|you are now|jailbreak|developer mode|"
    r"print (your |the )?(system )?prompt|show (your |the )?(system )?prompt|reveal (your |the )?(system )?prompt|"
    r"act as admin|bypass safety|disregard previous",
    re.I,
)

_ADMIN_PROBE_RE = re.compile(
    r"(show|list|get|display|dump|who are)( me)? (the )?admin (users|accounts|credentials|passwords|emails|data|members)|"
    r"admin (users|accounts|credentials|passwords|emails|data|secret|panel)|"
    r"(who is|who are) (the )?admin",
    re.I,
)


_BENGALI_CHAR_RE = re.compile(r"[\u0980-\u09FF]")

# Rate limit: 20 requests per 10 minutes (600s) per IP
_RATE_LIMIT_WINDOW = 600.0
_RATE_LIMIT_MAX = 20
_ip_requests: dict[str, deque[float]] = {}

MAX_MESSAGE_CHARS = 1000
MAX_TURNS = 6
MAX_REPLY_WORDS = 250


# Models
class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., max_length=5000)


class HelpChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1)
    lang: Literal["en", "bn"] = "en"
    page: str = Field("/", max_length=100)


class HelpChatResponse(BaseModel):
    reply: str
    lang: Literal["en", "bn"]
    source: Literal["llm", "faq"]


# In-memory FAQ Fallback
FAQ_ENTRIES = [
    {
        "keywords": ["crash-test", "run", "start", "decision", "freeze", "as_of", "কিভাবে", "ক্র্যাশ-টেস্ট"],
        "en": (
            "To run a Crash-Test on the /crash-test page:\n"
            "1. Select a company by name or SEC CIK (e.g. 719739 for SVB, 320193 for Apple).\n"
            "2. (Optional) Choose an Evidence Freeze Date (as_of) to exclude filings after that date.\n"
            "3. (Optional) Enter your proposed decision text (e.g. deposit partnership or credit line).\n"
            "4. Click 'Run Crash-Test' or choose a precomputed demo for instant results."
        ),
        "bn": (
            "/crash-test পেজে ক্র্যাশ-টেস্ট চালানোর নিয়ম:\n"
            "১. কোম্পানির নাম বা SEC CIK নম্বর নির্বাচন করুন (যেমন SVB-এর জন্য 719739)।\n"
            "২. প্রয়োজনে এভিডেন্স ফ্রিজ ডেট নির্ধারণ করুন (ঐ তারিখের পরের ফাইলিং অদৃশ্য থাকবে)।\n"
            "৩. আপনার প্রস্তাবিত সিদ্ধান্তের বিবরণ লিখুন (যেমন আমানত বা ক্রেডিট চুক্তি)।\n"
            "৪. 'Run Crash-Test'-এ ক্লিক করুন অথবা তাৎক্ষণিক ফলাফলের জন্য ডেমো বেছে নিন।"
        ),
    },
    {
        "keywords": ["health", "score", "band", "coverage", "insufficient", "স্কোর", "হেলথ"],
        "en": (
            "The Governance Health Score (0–100) measures overall corporate governance strength:\n"
            "- 85–100: Low Risk (robust compliance, few gaps)\n"
            "- 70–84: Moderate Risk (some omissions or potential conflicts)\n"
            "- 50–69: Elevated Risk (substantial governance gaps)\n"
            "- Below 50: High Risk (critical rule failures)\n"
            "Nirikkha never hides missing evidence: any 'Insufficient Evidence' items are reported transparently alongside the score."
        ),
        "bn": (
            "গভর্ন্যান্স হেলথ স্কোর (০–১০০) কোম্পানির প্রাতিষ্ঠানিক সুশাসন পরিমাপ করে:\n"
            "- ৮৫–১০০: কম ঝুঁকি (দৃঢ় নিয়মকানুন ও প্রমাণ)\n"
            "- ৭০–৮৪: মাঝারি ঝুঁকি (কিছু ঘাটতি বা পর্যালোচনাযোগ্য সম্পর্ক)\n"
            "- ৫০–৬৯: সতর্কতামূলক ঝুঁকি (উল্লেখযোগ্য তথ্যের অসঙ্গতি)\n"
            "- ৫০-এর নিচে: উচ্চ ঝুঁকি (গুরুত্বপূর্ণ নিয়মের ব্যর্থতা)\n"
            "যেকোনো অপর্যাপ্ত প্রমাণ স্কোরের পাশে স্বচ্ছভাবে দেখানো হয়।"
        ),
    },
    {
        "keywords": ["replay", "svb", "hindsight", "warning", "রিপ্লে"],
        "en": (
            "The First Warning Sign Replay (/replay) stress-tests Nirikkha against historical controversies like Silicon Valley Bank (SVB).\n"
            "- Freeze Date: March 7, 2023 (before failure announcements).\n"
            "- Hindsight Guard: Excludes post-crisis news.\n"
            "- Result: Out of 5 knowable signs, 2 were detected and 3 questioned; 0 knowable signs were missed. Verdict: VALID."
        ),
        "bn": (
            "ফার্স্ট ওয়ার্নিং সাইন রিপ্লে (/replay) অতীতের আর্থিক বিপর্যয়ে নিরীক্ষার সতর্কতা যাচাই করে:\n"
            "- ফ্রিজ তারিখ: ৭ মার্চ ২০২৩ (সংকটের আগের দিন)।\n"
            "- হাইন্ডসাইট গার্ড: সংকটের পরের কোনো তথ্য মডেলে প্রবেশ করতে পারে না।\n"
            "- ফলাফল: ৫টি জানার যোগ্য লক্ষণের মধ্যে ২টি শনাক্ত এবং ৩টি প্রশ্নবিদ্ধ হয়েছে; কোনো লক্ষণ বাদ পড়েনি। রায়: VALID।"
        ),
    },
    {
        "keywords": ["radar", "approve", "reject", "alert", "রেডার"],
        "en": (
            "The Regulatory Change Radar (/radar) monitors two streams: curated SEC rule changes and newly filed EDGAR disclosures.\n"
            "Reviewers click 'Approve' to schedule diligence or 'Reject' to dismiss. All human decisions are logged in an audit trail."
        ),
        "bn": (
            "রেগুলেটরি চেঞ্জ রেডার (/radar) দুটি প্রবাহ পর্যবেক্ষণ করে: এসইসি বিধিমালার পরিবর্তন এবং নতুন ফাইলিং।\n"
            "পর্যালোচক 'Approve' চেপে পরবর্তী যাচাই শুরু করতে পারেন অথবা 'Reject' করতে পারেন। প্রতিটি সিদ্ধান্ত অডিট ট্রেইলে সংরক্ষিত থাকে।"
        ),
    },
    {
        "keywords": ["price", "pricing", "cost", "plan", "free", "pro", "team", "enterprise", "মূল্য", "প্ল্যান"],
        "en": (
            "Nirikkha Plans:\n"
            "- Free: $0/mo (3 Crash-Tests/mo, summary report, SEC evidence links)\n"
            "- Analyst Pro: $49/user/mo (30 Crash-Tests/mo, full Rule Engine, PDF export, Radar for 10 companies)\n"
            "- Team: $399/mo (150 Crash-Tests/mo, shared workspace, Radar for 50 companies)\n"
            "- Enterprise: Annual contract (pricing agreed per customer; start with \"Request a Pilot\"). For banks, institutional investors and large compliance teams: approved private documents, deployment on the customer's own servers so data does not leave their environment, custom rules, SSO, and unlimited use."
        ),
        "bn": (
            "নিরীক্ষার সাবস্ক্রিপশন প্ল্যানসমূহ:\n"
            "- Free: $০/মাস (৩টি ক্র্যাশ-টেস্ট, সারসংক্ষেপ ও ফাইলিং লিংক)\n"
            "- Analyst Pro: $৪৯/ব্যবহারকারী/মাস (৩০টি টেস্ট, সম্পূর্ণ রুল ইঞ্জিন, পিডিএফ ও ১০টি কোম্পানির রেডার)\n"
            "- Team: $৩৯৯/মাস (১৫০টি টেস্ট, শেয়ার্ড ওয়ার্কস্পেস, ৫০টি কোম্পানির রেডার)\n"
            "- Enterprise: বার্ষিক চুক্তি (গ্রাহকভিত্তিক নির্ধারিত মূল্য; 'Request a Pilot' দিয়ে শুরু)। ব্যাংক ও প্রাতিষ্ঠানিক টিমের জন্য: অনুমোদিত নিজস্ব নথি, গ্রাহকের নিজস্ব সার্ভারে ডেটা সংরক্ষণ, কাস্টম রুলস, SSO ও আনলিমিটেড ব্যবহার।"
        ),
    },

    {
        "keywords": ["graph", "relationship", "interlock", "গ্রাফ"],
        "en": (
            "The Relationship Graph (/graph) maps corporate directors, executive officers, committees, and outside entities using Neo4j.\n"
            "It highlights 'interlocks' (outside organizations shared by two or more insiders) to surface potential conflicts of interest."
        ),
        "bn": (
            "রিলেশনশিপ গ্রাফ (/graph) পরিচালক, নির্বাহী কর্মকর্তা ও কমিটির পারস্পরিক সম্পর্ক মানচিত্রে প্রদর্শন করে।\n"
            "এটি 'ইন্টারলক' বা একাধিক পরিচালকের মধ্যকার অভিন্ন বাইরের প্রতিষ্ঠান চিহ্নিত করে।"
        ),
    },
    {
        "keywords": ["loading", "stuck", "timeout", "wake", "server", "লোডিং", "দেরি"],
        "en": (
            "If your report is taking time:\n"
            "1. Free-tier cloud backend spins down on idle; the first request may take 45–60 seconds to wake up.\n"
            "2. A live test runs 4 parallel deep investigations and takes 1–3 minutes.\n"
            "3. You can view precomputed demo reports (e.g. SVB) instantly on the Reports page."
        ),
        "bn": (
            "রিপোর্ট লোড হতে দেরি হলে:\n"
            "১. ক্লাউড ব্যাকএন্ড নিষ্ক্রিয় থাকলে চালু হতে ৪৫–৬০ সেকেন্ড লাগতে পারে।\n"
            "২. একটি লাইভ টেস্ট ৪টি সমান্তরাল তদন্ত সম্পন্ন করতে ১–৩ মিনিট সময় নেয়।\n"
            "৩. তাৎক্ষণিক ফলাফলের জন্য প্রিকম্পিউটেড ডেমো রিপোর্ট (যেমন SVB) দেখতে পারেন।"
        ),
    },
    {
        "keywords": ["advice", "legal", "invest", "আইনি", "পরামর্শ"],
        "en": (
            "Nirikkha provides governance evidence analysis of public SEC filings. It does NOT provide legal, financial, or investment advice."
        ),
        "bn": (
            "নিরীক্ষা পাবলিক এসইসি ফাইলিং থেকে তথ্য-ভিত্তিক গভর্ন্যান্স বিশ্লেষণ প্রদান করে। এটি কোনো আইনি, বিনিয়োগ বা আর্থিক পরামর্শ নয়।"
        ),
    },
]


def _check_rate_limit(client_ip: str) -> None:
    now = time.monotonic()
    queue = _ip_requests.setdefault(client_ip, deque())
    while queue and now - queue[0] > _RATE_LIMIT_WINDOW:
        queue.popleft()
    if len(queue) >= _RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many help requests. Please wait a few minutes and try again.",
        )
    queue.append(now)


def _reset_rate_limits() -> None:
    """Helper for testing rate limit behavior."""
    _ip_requests.clear()


def _load_kb() -> str:
    if _KB_PATH.exists():
        try:
            return _KB_PATH.read_text(encoding="utf-8")
        except OSError:
            pass
    return "Nirikkha Governance Crash-Test AI reads SEC filings (10-K, DEF 14A) and evaluates governance evidence."


def _load_system_prompt(page: str, lang: str) -> str:
    kb = _load_kb()
    if _PROMPT_PATH.exists():
        try:
            text = _PROMPT_PATH.read_text(encoding="utf-8")
            return text.replace("{knowledge_base}", kb).replace("{current_page}", page).replace("{lang}", lang)
        except OSError:
            pass
    return f"You are Nirikkha Guide. Answer using this knowledge base:\n{kb}"


def _get_faq_fallback(query: str, lang: str) -> str:
    query_lower = query.lower()
    for entry in FAQ_ENTRIES:
        if any(kw in query_lower for kw in entry["keywords"]):
            return entry[lang] if lang in ("en", "bn") else entry["en"]

    if lang == "bn":
        return (
            "আমি নিরীক্ষা গাইড। আপনার প্রশ্নের নির্দিষ্ট উত্তরটি আমাদের পাবলিক গাইডে পাওয়া যায়নি। "
            "বিস্তারিত জানার জন্য অনুগ্রহ করে /docs দেখুন অথবা প্রাইসিং পেজ থেকে 'Request a Pilot' অনুরোধ করুন।"
        )
    return (
        "I am Nirikkha Guide. I could not find a specific answer to that in our public product guide. "
        "Please visit /docs or 'Request a Pilot' on the Pricing page for further assistance."
    )


def _detect_lang(text: str, default: Literal["en", "bn"]) -> Literal["en", "bn"]:
    if _BENGALI_CHAR_RE.search(text):
        return "bn"
    return default


def _trim_words(text: str, max_words: int = MAX_REPLY_WORDS) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."


@router.post("/chat", response_model=HelpChatResponse)
def help_chat(body: HelpChatRequest, request: Request) -> HelpChatResponse:
    # 1. Rate limiting by IP
    # Behind Render's proxy every request shares one socket IP, so use the forwarded client IP.
    # These headers can be spoofed; this limit only slows abuse, it is not an access control.
    forwarded = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for", "")
    client_ip = forwarded.split(",")[0].strip() or (request.client.host if request.client else "127.0.0.1")
    _check_rate_limit(client_ip)

    # 2. Extract and validate latest user message
    user_messages = [m for m in body.messages if m.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No user message provided.")

    latest_msg = user_messages[-1].content.strip()
    if len(latest_msg) > MAX_MESSAGE_CHARS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Message exceeds {MAX_MESSAGE_CHARS} characters.",
        )

    # Language resolution
    lang = _detect_lang(latest_msg, body.lang)

    # 3. Guard against Prompt Injections
    if _INJECTION_RE.search(latest_msg):
        refusal = (
            "আমি নিরীক্ষা গাইড। আমি আমার নিরাপত্তা নির্দেশনা পরিবর্তন বা অভ্যন্তরীণ প্রম্পট প্রদর্শন করতে পারি না। "
            "নিরীক্ষার ফিচার বা ব্যবহার সংক্রান্ত কীভাবে সাহায্য করতে পারি?"
            if lang == "bn"
            else "I am Nirikkha Guide. I cannot override my safety instructions or display internal prompts. "
            "How can I help you explore Nirikkha's features today?"
        )
        return HelpChatResponse(reply=refusal, lang=lang, source="faq")

    # 4. Guard against Admin Data Probing
    if _ADMIN_PROBE_RE.search(latest_msg):
        refusal = (
            "অ্যাডমিন প্যানেল শুধুমাত্র অভ্যন্তরীণ কর্মীদের জন্য সংরক্ষিত এবং এর জন্য অনুমোদিত স্টাফ অ্যাকাউন্ট প্রয়োজন। "
            "আমি কোনো প্রশাসনিক অ্যাকাউন্ট বা সিস্টেমের অভ্যন্তরীণ তথ্য প্রদর্শন করতে পারি না।"
            if lang == "bn"
            else "The Admin area is reserved for internal staff and requires a staff account. "
            "I cannot display administrator accounts or sensitive system data."
        )
        return HelpChatResponse(reply=refusal, lang=lang, source="faq")

    # 5. PII Redaction on user message
    redacted_input, _ = redact_pii(latest_msg)

    # 6. Format context window (limit to at most last MAX_TURNS messages)
    history = body.messages[-MAX_TURNS:]
    system_prompt = _load_system_prompt(body.page, lang)

    llm_messages = [{"role": "system", "content": system_prompt}]
    for m in history:
        # Use redacted input for the latest message
        c = redacted_input if m == history[-1] and m.role == "user" else m.content
        llm_messages.append({"role": m.role, "content": c})

    # 7. LLM Call via the fast route with fallback to FAQ
    try:
        llm = get_llm()
        result = llm.complete("fast", llm_messages, max_tokens=350, temperature=0.0, use_cache=True)
        reply_text = result.text.strip()
        # PII redaction on model reply
        redacted_reply, _ = redact_pii(reply_text)
        final_reply = _trim_words(redacted_reply)
        return HelpChatResponse(reply=final_reply, lang=lang, source="llm")
    except (LLMError, Exception):

        fallback_reply = _get_faq_fallback(latest_msg, lang)
        return HelpChatResponse(reply=fallback_reply, lang=lang, source="faq")
