"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PipelineDiagram } from "../../components/pipeline-diagram";
import { useApp } from "../../components/providers";
import { API_URL, getHealth, getStatus, type ServerHealth, type Status } from "../../lib/api";

import ResultGlossaryI18n from "../../components/result-glossary-i18n";
const REPO = "https://github.com/ShArafat58/nirikkha";

const MODELS = [
  { task: "reason", model: "openai/gpt-oss-120b (Groq)", why: "Legal memo and the Sentinel's citation judge: strongest open reasoning model on the free tier." },
  { task: "fast", model: "openai/gpt-oss-20b (Groq)", why: "Turning a decision into investigation questions: fast and cheap." },
  { task: "analyze", model: "Gemini 2.5 Flash → gpt-oss-120b", why: "Answering only from the evidence pack; long context, with a fallback if the first is busy." },
  { task: "extract", model: "Qwen3 (Groq)", why: "Extracting directors, officers, committees and related parties as JSON from proxy statements." },
  { task: "safety", model: "openai/gpt-oss-safeguard-20b (Groq)", why: "Prompt-injection and abuse check on every request before any other model." },
  { task: "bangla", model: "Gemini 2.5 Flash", why: "Bengali translation of memos, keeping quotes and rule names in English." },
  { task: "embed", model: "BAAI/bge-small-en-v1.5 (local, ONNX)", why: "384-dimension embeddings on our own machine: no API cost, no data leaves." },
  { task: "rerank", model: "ms-marco-MiniLM-L-6-v2 (local)", why: "Cross-encoder reranking lifted hit@1 from 50% to 90% on our gold set." },
];

const RULES = [
  ["law", "R401_DIRECTORS", "Reg S-K 401: directors identified"], ["law", "R401_OTHER_BOARDS", "Reg S-K 401: other public boards"],
  ["law", "R402_SCT", "Reg S-K 402(c): Summary Compensation Table"], ["law", "R402_PVP", "Reg S-K 402(v): pay versus performance"],
  ["law", "R404_POLICY", "Reg S-K 404(b): related-person policy"], ["law", "R404_TRANSACTIONS", "Reg S-K 404(a): transactions above $120,000"],
  ["law", "R407_INDEPENDENCE", "Reg S-K 407(a): director independence"], ["law", "R407_FIN_EXPERT", "Reg S-K 407(d)(5): audit committee financial expert"],
  ["law", "R407_RISK_OVERSIGHT", "Reg S-K 407(h): board risk oversight"],
  ["best_practice", "BP_RISK_COMMITTEE", "Dedicated risk committee"], ["best_practice", "BP_CRO", "Chief Risk Officer (financial sector only)"],
  ["internal_indicator", "II_DISCLOSURE_FRESHNESS", "Proxy not older than ~15 months"], ["internal_indicator", "II_YOY_CHANGE", "Large year-over-year change in risk sections"],
  ["internal_indicator", "II_OFFICER_OUTSIDE_ROLES", "Executive outside board seats"], ["internal_indicator", "II_COMMITTEE_CHAIR_CONSISTENCY", "One chair per committee"],
  ["internal_indicator", "II_RISK_LEADERSHIP_CHANGE", "CRO or CFO change or vacancy"],
];

const EVAL = [
  { k: "Retrieval hit@1 / hit@3 / MRR", v: "90% / 100% / 0.933", n: "10 gold questions, hybrid + rerank (hybrid alone: 50% / 70% / 0.567)" },
  { k: "Prompt-injection attacks blocked", v: "6 / 6, 0 false positives on 6 benign", n: "Optimistic: the attacks were written knowing the patterns" },
  { k: "PII caught / public text altered", v: "8 / 8 · 0 / 6", n: "Emails, phones, SSN, cards (Luhn), IBAN, IP; CIK and accession numbers protected" },
  { k: "Legal memo citation pass rate", v: "1.0", n: "Every rule and finding id in the memo is checked against the report by code" },
  { k: "Relationship extraction accuracy", v: "85%", n: "Spot-checked sample; unverified relations are dropped" },
  { k: "SVB Replay (evidence frozen 2023-03-07)", v: "5 of 5 knowable signs raised", n: "2 flagged, 3 raised as questions, 0 missed, 1 not knowable; 0 post-freeze citations" },
];

const TXT = {
  en: {
    kicker: "Documentation", title: "How Nirikkha works", sub: "Architecture, models, rules, evaluation and the limits we know about. Everything here is checkable in the repository.",
    nav: ["Status", "Pipeline", "Architecture", "Models", "Rules", "Evaluation", "Responsible AI", "Limitations", "Links"],
    status: "System status", backend: "Backend", worker: "Analysis worker", mode: "Live mode", version: "Version", online: "online", offline: "offline",
    unreachable: "unreachable (the free server may be waking up)",
    pipe: "Crash-Test pipeline (LangGraph)", pipeNote: "Severity and confidence are kept apart. Insufficient evidence is listed, never scored as low risk.",
    arch: "Architecture and data stack", models: "Models and why", task: "Task", model: "Model", why: "Why",
    rules: "Governance Rule Engine", rulesNote: "Structured, testable rules with four results: Pass, Potential gap, Fail, Insufficient evidence. Applicable law, best practice and internal indicators are kept separate.",
    evalT: "Evaluation", evalNote: "From the latest run of python -m evaluation.run (docs/EVALUATION.md).",
    resp: "Responsible AI", limits: "Known limitations", links: "Links",
  },
  bn: {
    kicker: "ডকুমেন্টেশন", title: "Nirikkha কীভাবে কাজ করে", sub: "আর্কিটেকচার, মডেল, নিয়ম, মূল্যায়ন আর আমাদের জানা সীমাবদ্ধতা। এখানকার সবকিছু রিপোজিটরিতে যাচাই করা যায়।",
    nav: ["অবস্থা", "পাইপলাইন", "আর্কিটেকচার", "মডেল", "নিয়ম", "মূল্যায়ন", "দায়িত্বশীল AI", "সীমাবদ্ধতা", "লিংক"],
    status: "সিস্টেমের অবস্থা", backend: "ব্যাকএন্ড", worker: "বিশ্লেষণ ওয়ার্কার", mode: "লাইভ মোড", version: "সংস্করণ", online: "চালু", offline: "বন্ধ",
    unreachable: "পাওয়া যাচ্ছে না (ফ্রি সার্ভার জেগে উঠছে হয়তো)",
    pipe: "ক্র্যাশ-টেস্ট পাইপলাইন (LangGraph)", pipeNote: "ঝুঁকির মাত্রা আর প্রমাণের আস্থা আলাদা রাখা হয়। অপর্যাপ্ত প্রমাণ তালিকায় থাকে, কখনো কম ঝুঁকি বলে গোনা হয় না।",
    arch: "আর্কিটেকচার ও ডেটা স্ট্যাক", models: "মডেল ও কেন", task: "কাজ", model: "মডেল", why: "কেন",
    rules: "গভর্ন্যান্স রুল ইঞ্জিন", rulesNote: "কাঠামোবদ্ধ, পরীক্ষাযোগ্য নিয়ম; ফল চার রকম: পাস, সম্ভাব্য ঘাটতি, ফেল, অপর্যাপ্ত প্রমাণ। আইন, ভালো চর্চা আর অভ্যন্তরীণ সূচক আলাদা।",
    evalT: "মূল্যায়ন", evalNote: "python -m evaluation.run-এর সর্বশেষ রান থেকে (docs/EVALUATION.md)।",
    resp: "দায়িত্বশীল AI", limits: "জানা সীমাবদ্ধতা", links: "লিংক",
  },
};

const ARCH = [
  ["Frontend", "Next.js on Vercel · EN/BN · mock mode for design work"],
  ["API", "FastAPI on Render · OpenAPI docs · auth (argon2id, JWT), billing simulation, admin"],
  ["Worker", "Runs the full pipeline (two local ONNX models) and claims queued jobs from Postgres"],
  ["Orchestration", "LangGraph state graph with per-node progress events"],
  ["Search", "Supabase Postgres + pgvector (HNSW, 384-d) and full-text (GIN), fused with RRF, then cross-encoder rerank"],
  ["Graph", "Neo4j Aura: people, committees, companies, outside organizations, related parties"],
  ["Warehouse", "DuckDB: sections and year-over-year disclosure changes"],
  ["Sources", "SEC EDGAR (10-K, DEF 14A, PRE 14A, 8-K) with a named User-Agent and rate limiting; curated SEC rule changes"],
  ["LLMs", "Groq and Gemini free tiers through one router: caching, per-model budgets, retries and fallbacks; token and cost log per run"],
];

const RESP = [
  "Every finding cites the source document, page and passage.",
  "Evidence confidence and risk severity are separate; the Sentinel can only lower confidence, never severity.",
  "Insufficient evidence is reported, not hidden in the score.",
  "Uncertain findings and every Radar alert wait for human review, with an audit trail.",
  "Personal data is redacted before any model; the date of birth is checked for 18+ but not stored.",
  "Prompt-injection guard on every request; payment flows are simulated, no card or account data is collected.",
  "A disclosed relationship is presented as a question to check, never as misconduct.",
];

const LIMITS = [
  "US SEC filings only for now; other registries (Companies House, GLEIF) are future work.",
  "Extraction can misread tables; table rows must name a committee to count, and unverified relations are dropped.",
  "Radar applicability is estimated from filing dates; the real trigger is the fiscal year end, so a person confirms each alert.",
  "Two rules (risk leadership change, CRO only for financial firms) were refined while building the SVB replay; the Apple control shows they do not flag every company.",
  "LLM answers vary between runs; stored demo runs are fixed so results can be reproduced.",
  "Free-tier servers sleep: the first request after idle can take up to a minute.",
];

export default function DocsPage() {
  const app = useApp();
  const lang = (app as unknown as { lang?: string }).lang === "bn" ? "bn" : "en";
  const t = TXT[lang];
  const [health, setHealth] = useState<ServerHealth | null>(null);
  const [status, setStatus] = useState<Status | null>(null);
  const [down, setDown] = useState(false);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setDown(true));
    getStatus().then(setStatus).catch(() => setDown(true));
  }, []);

  const panel = "rounded-2xl border border-slate-500/20 bg-slate-500/[0.04] p-5 sm:p-6";
  const ids = ["status", "pipeline", "architecture", "models", "rules", "evaluation", "responsible", "limitations", "links"];
  const H = ({ i, children }: { i: number; children: string }) => (
    <h2 id={ids[i]} className="scroll-mt-24 text-xl font-bold sm:text-2xl">{children}</h2>
  );
  const dot = (ok: boolean | null) => <span className={`inline-block h-2.5 w-2.5 rounded-full ${ok == null ? "bg-slate-500" : ok ? "bg-emerald-500" : "bg-rose-500"}`} />;

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:py-10">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-amber-500">{t.kicker}</p>
      <h1 className="mt-2 text-3xl font-bold sm:text-4xl">{t.title}</h1>
      <p className="mt-3 max-w-3xl opacity-75">{t.sub}</p>

      <nav className="mt-6 flex flex-wrap gap-2 text-sm">
        {t.nav.map((n, i) => <a key={n} href={`#${ids[i]}`} className="rounded-full border border-slate-500/30 px-3 py-1 opacity-80 hover:border-amber-500 hover:text-amber-500">{n}</a>)}
      </nav>

      <div className="mt-10 space-y-14">
        <section className="space-y-4">
          <H i={0}>{t.status}</H>
          <div className="grid gap-3 sm:grid-cols-4">
            <div className={panel}><p className="text-xs opacity-60">{t.backend}</p>
              <p className="mt-1 flex items-center gap-2 font-semibold">{dot(health ? health.status === "ok" : down ? false : null)}
                {health ? health.status : down ? t.unreachable : "…"}</p></div>
            <div className={panel}><p className="text-xs opacity-60">{t.worker}</p>
              <p className="mt-1 flex items-center gap-2 font-semibold">{dot(status ? status.worker_online : null)}
                {status ? (status.worker_online ? t.online : t.offline) : "…"}</p></div>
            <div className={panel}><p className="text-xs opacity-60">{t.mode}</p><p className="mt-1 font-semibold">{status?.live_mode ?? "…"}</p></div>
            <div className={panel}><p className="text-xs opacity-60">{t.version}</p><p className="mt-1 font-mono text-sm">{health ? `${health.app} ${health.version} · ${health.env}` : "…"}</p></div>
          </div>
        </section>

        <section className="space-y-4">
          <H i={1}>{t.pipe}</H>
          <PipelineDiagram lang={lang} />
          <p className="text-sm opacity-70">{t.pipeNote}</p>
        </section>

        <section className="space-y-4">
          <H i={2}>{t.arch}</H>
          <div className="grid gap-3 md:grid-cols-3">
            {ARCH.map(([k, v]) => <div key={k} className={panel}><p className="text-xs font-semibold uppercase tracking-wider text-sky-500">{k}</p><p className="mt-2 text-sm leading-relaxed opacity-85">{v}</p></div>)}
          </div>
        </section>

        <section className="space-y-4">
          <H i={3}>{t.models}</H>
          <div className="overflow-x-auto rounded-2xl border border-slate-500/20">
            <table className="w-full min-w-[720px] text-sm">
              <thead className="bg-slate-500/10 text-left text-xs uppercase tracking-wider opacity-70">
                <tr><th className="px-4 py-2">{t.task}</th><th className="px-4 py-2">{t.model}</th><th className="px-4 py-2">{t.why}</th></tr>
              </thead>
              <tbody>
                {MODELS.map((m) => (
                  <tr key={m.task} className="border-t border-slate-500/15">
                    <td className="px-4 py-3 font-mono text-xs">{m.task}</td><td className="px-4 py-3 font-medium">{m.model}</td>
                    <td className="px-4 py-3 opacity-80" lang="en">{m.why}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="space-y-4">
          <H i={4}>{t.rules}</H>
          <p className="text-sm opacity-70">{t.rulesNote}</p>
          <div className="grid gap-4 md:grid-cols-3">
            {(["law", "best_practice", "internal_indicator"] as const).map((cat) => (
              <div key={cat} className={panel}>
                <p className="text-xs font-semibold uppercase tracking-wider text-emerald-500">{cat.replace("_", " ")}</p>
                <ul className="mt-3 space-y-2 text-sm">
                  {RULES.filter((r) => r[0] === cat).map((r) => (
                    <li key={r[1]}><span className="font-mono text-[11px] opacity-60">{r[1]}</span><br /><span lang="en">{r[2]}</span></li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        <section className="space-y-4">
          <H i={5}>{t.evalT}</H>
          <p className="text-sm opacity-70">{t.evalNote}</p>
          <div className="grid gap-3 md:grid-cols-2">
            {EVAL.map((e) => (
              <div key={e.k} className={panel}>
                <p className="text-sm opacity-70" lang="en">{e.k}</p>
                <p className="mt-1 text-2xl font-bold text-amber-500">{e.v}</p>
                <p className="mt-1 text-xs opacity-60" lang="en">{e.n}</p>
              </div>
            ))}
          </div>
          <a href={`${API_URL}/api/evaluation`} target="_blank" rel="noreferrer" className="inline-block text-sm text-sky-500 hover:underline">Live evaluation JSON ↗</a>
        </section>

        <section className="space-y-4">
          <H i={6}>{t.resp}</H>
          <ul className="grid gap-3 md:grid-cols-2">
            {RESP.map((r) => <li key={r} className={`${panel} text-sm`} lang="en"><span className="text-emerald-500">✓</span> {r}</li>)}
          </ul>
        </section>

        <section className="space-y-4">
          <H i={7}>{t.limits}</H>
          <ul className="space-y-2">
            {LIMITS.map((l) => <li key={l} className="rounded-xl border border-amber-500/30 bg-amber-500/[0.05] px-4 py-3 text-sm" lang="en">⚠ {l}</li>)}
          </ul>
        </section>

        <section className="space-y-4">
          <H i={8}>{t.links}</H>
          <div className="flex flex-wrap gap-3 text-sm">
            <a href={`${API_URL}/docs`} target="_blank" rel="noreferrer" className="rounded-lg border border-slate-500/30 px-4 py-2 hover:border-amber-500">API (OpenAPI) ↗</a>
            <a href={REPO} target="_blank" rel="noreferrer" className="rounded-lg border border-slate-500/30 px-4 py-2 hover:border-amber-500">GitHub ↗</a>
            <Link href="/replay" className="rounded-lg border border-slate-500/30 px-4 py-2 hover:border-amber-500">Replay</Link>
            <Link href="/graph" className="rounded-lg border border-slate-500/30 px-4 py-2 hover:border-amber-500">Graph</Link>
            <Link href="/radar" className="rounded-lg border border-slate-500/30 px-4 py-2 hover:border-amber-500">Radar</Link>
            <Link href="/pricing" className="rounded-lg border border-slate-500/30 px-4 py-2 hover:border-amber-500">Pricing</Link>
          </div>
        </section>
      </div>
    <ResultGlossaryI18n />
      </main>
  );
}