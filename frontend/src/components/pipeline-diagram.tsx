// The Crash-Test LangGraph pipeline as four colour-coded phases, with the parallel investigation fan-out.
type L = "en" | "bn";
type Step = { id: string; icon: string; en: string; bn: string; d: string; branches?: { icon: string; en: string; bn: string }[] };
type Phase = { key: string; en: string; bn: string; tone: string; ring: string; text: string; steps: Step[] };

const PHASES: Phase[] = [
  { key: "protect", en: "Protect", bn: "সুরক্ষা", tone: "from-rose-500/15", ring: "border-rose-500/40", text: "text-rose-400", steps: [
    { id: "redact", icon: "🧹", en: "Remove personal data", bn: "ব্যক্তিগত তথ্য মুছে ফেলা", d: "PII redaction" },
    { id: "guard", icon: "🛡️", en: "Safety check", bn: "নিরাপত্তা যাচাই", d: "gpt-oss-safeguard-20b" },
  ] },
  { key: "gather", en: "Gather", bn: "সংগ্রহ", tone: "from-sky-500/15", ring: "border-sky-500/40", text: "text-sky-400", steps: [
    { id: "collect", icon: "🗂️", en: "Load filings, graph, rules", bn: "ফাইলিং, গ্রাফ, নিয়ম লোড", d: "evidence frozen at the date" },
    { id: "plan", icon: "🧭", en: "Decision → questions", bn: "সিদ্ধান্ত → প্রশ্ন", d: "gpt-oss-20b" },
    { id: "gather", icon: "🔎", en: "Find evidence passages", bn: "প্রমাণ খোঁজা", d: "pgvector + full-text + rerank" },
  ] },
  { key: "reason", en: "Reason", bn: "বিশ্লেষণ", tone: "from-amber-500/15", ring: "border-amber-500/40", text: "text-amber-400", steps: [
    { id: "analyze", icon: "🧠", en: "Answer from evidence only", bn: "শুধু প্রমাণ থেকে উত্তর", d: "Gemini 2.5 Flash → gpt-oss-120b" },
    { id: "investigate", icon: "🧪", en: "Four investigations", bn: "চারটি অনুসন্ধান", d: "run in parallel", branches: [
      { icon: "🕸️", en: "Relationship", bn: "সম্পর্ক" }, { icon: "🔁", en: "Consistency", bn: "সামঞ্জস্য" },
      { icon: "⚖️", en: "Rules", bn: "নিয়ম" }, { icon: "❓", en: "Missing evidence", bn: "অনুপস্থিত প্রমাণ" },
    ] },
    { id: "merge", icon: "🧩", en: "Merge findings", bn: "ফাইন্ডিং একত্র", d: "deterministic" },
  ] },
  { key: "verify", en: "Verify", bn: "যাচাই", tone: "from-emerald-500/15", ring: "border-emerald-500/40", text: "text-emerald-400", steps: [
    { id: "sentinel", icon: "✅", en: "Reliability Sentinel", bn: "রিলায়েবিলিটি সেন্টিনেল", d: "gpt-oss-120b checks every citation" },
    { id: "score", icon: "📊", en: "Health Score", bn: "হেলথ স্কোর", d: "severity × confidence, gaps listed" },
    { id: "report", icon: "📄", en: "Cited report + legal memo", bn: "উদ্ধৃতিসহ রিপোর্ট + মেমো", d: "EN / BN" },
  ] },
];

const CSS = `
@keyframes nk-travel { 0% { left: 0%; opacity: 0 } 8% { opacity: 1 } 92% { opacity: 1 } 100% { left: 100%; opacity: 0 } }
@keyframes nk-flow { to { background-position: 0 24px } }
.nk-dot { animation: nk-travel 6s linear infinite; }
.nk-flow { background-image: repeating-linear-gradient(to bottom, currentColor 0 6px, transparent 6px 12px); background-size: 2px 24px; animation: nk-flow 0.9s linear infinite; }
@media (prefers-reduced-motion: reduce) { .nk-dot, .nk-flow { animation: none; } }
`;

export function PipelineDiagram({ lang }: { lang: L }) {
  let n = 0;
  return (
    <div className="space-y-5">
      <style>{CSS}</style>
      <div className="relative hidden h-1.5 rounded-full bg-gradient-to-r from-rose-500/50 via-sky-500/50 via-amber-500/50 to-emerald-500/60 md:block">
        <span className="nk-dot absolute -top-1.5 h-4 w-4 -translate-x-1/2 rounded-full bg-white shadow-[0_0_16px_6px_rgba(245,184,61,0.55)]" />
      </div>
      <div className="grid gap-4 md:grid-cols-4 md:gap-3">
        {PHASES.map((ph, pi) => (
          <div key={ph.key} className="relative">
            <div className={`h-full rounded-2xl border ${ph.ring} bg-gradient-to-b ${ph.tone} to-transparent p-4`}>
              <p className={`text-[11px] font-bold uppercase tracking-[0.2em] ${ph.text}`}>{pi + 1} · {lang === "bn" ? ph.bn : ph.en}</p>
              <ol className="mt-3">
                {ph.steps.map((s, si) => {
                  n += 1;
                  return (
                    <li key={s.id}>
                      <div className="rounded-xl border border-slate-500/25 bg-slate-950/30 p-3 shadow-sm backdrop-blur">
                        <div className="flex items-start gap-3">
                          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-500/15 text-lg" aria-hidden>{s.icon}</span>
                          <div className="min-w-0">
                            <p className="font-mono text-[10px] opacity-50">{n}. {s.id}</p>
                            <p className="text-sm font-semibold leading-snug">{lang === "bn" ? s.bn : s.en}</p>
                            <p className="mt-0.5 text-[11px] opacity-60">{s.d}</p>
                          </div>
                        </div>
                        {s.branches && (
                          <div className="mt-3">
                            <p className="mb-1.5 text-[10px] uppercase tracking-wider opacity-50">{lang === "bn" ? "সমান্তরাল" : "parallel"} ⇉</p>
                            <div className="grid grid-cols-2 gap-1.5">
                              {s.branches.map((b) => (
                                <span key={b.en} className={`rounded-lg border ${ph.ring} px-2 py-1.5 text-[11px] font-medium`}>
                                  {b.icon} {lang === "bn" ? b.bn : b.en}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                      {si < ph.steps.length - 1 && <div className={`nk-flow mx-auto my-1 h-5 w-0.5 opacity-60 ${ph.text}`} aria-hidden />}
                    </li>
                  );
                })}
              </ol>
            </div>
            {pi < PHASES.length - 1 && (
              <>
                <span className={`absolute -right-3 top-1/2 z-10 hidden -translate-y-1/2 text-xl md:block ${PHASES[pi + 1].text}`} aria-hidden>➜</span>
                <div className={`nk-flow mx-auto mt-2 h-6 w-0.5 opacity-60 md:hidden ${ph.text}`} aria-hidden />
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}