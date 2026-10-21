"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { useApp } from "../../../../components/providers";
import { Markdown } from "../../../../components/report/markdown";
import { Alert, Button } from "../../../../components/ui";
import { draftMemo, getMemo, translateMemo, type MemoResponse } from "../../../../lib/memo";
import { Loader } from "../../../../components/loader";

const TXT = {
  en: {
    kicker: "Legal memo", title: "Governance risk memo", back: "Back to the report",
    none: "No memo has been drafted for this Crash-Test yet.", draft: "Draft legal memo", drafting: "Drafting… this can take up to a minute.",
    md: "Download .md", pdfEn: "PDF (English)", pdfBn: "PDF (বাংলা)", view: "Memo language",
    translating: "Translating into Bengali…",
    notice: "Not legal advice. A draft for a qualified lawyer to review. Every rule cited is checked against the Rule Engine, and every risk links to the findings it rests on.",
  },
  bn: {
    kicker: "লিগ্যাল মেমো", title: "গভর্ন্যান্স ঝুঁকির মেমো", back: "রিপোর্টে ফিরে যান",
    none: "এই ক্র্যাশ-টেস্টের জন্য এখনো কোনো মেমো লেখা হয়নি।", draft: "লিগ্যাল মেমো খসড়া করুন", drafting: "খসড়া হচ্ছে… এক মিনিট পর্যন্ত লাগতে পারে।",
    md: ".md ডাউনলোড", pdfEn: "PDF (English)", pdfBn: "PDF (বাংলা)", view: "মেমোর ভাষা",
    translating: "বাংলায় অনুবাদ হচ্ছে…",
    notice: "এটা আইনি পরামর্শ নয়। একজন যোগ্য আইনজীবীর পর্যালোচনার জন্য খসড়া। উদ্ধৃত প্রতিটি নিয়ম Rule Engine দিয়ে যাচাই করা, আর প্রতিটি ঝুঁকি তার ভিত্তি finding-এর সাথে যুক্ত।",
  },
};
const DOC = {
  en: { band: "Legal risk memo", footer: "Nirikkha · Governance Crash-Test AI · Trust less, Verify more", draft: "AI-generated draft · not legal advice", run: "Run" },
  bn: { band: "আইনি ঝুঁকির মেমো", footer: "নিরীক্ষা · গভর্ন্যান্স ক্র্যাশ-টেস্ট AI · Trust less, Verify more", draft: "AI-তৈরি খসড়া · আইনি পরামর্শ নয়", run: "রান" },
};

const PRINT_CSS = `
@media print {
  @page { size: A4; margin: 0; }
  html, body { background: #ffffff !important; }
  body * { visibility: hidden !important; }
  .memo-doc, .memo-doc * { visibility: visible !important; opacity: 1 !important; }
  .memo-doc { position: absolute; left: 0; top: 0; width: 100%; margin: 0 !important; border: 0 !important;
              border-radius: 0 !important; box-shadow: none !important; padding: 0 !important; }
  .memo-body { padding: 10mm 16mm 18mm !important; }
  .memo-band, .memo-doc .bg-slate-50, .memo-doc [class*="bg-rose-"], .memo-doc [class*="bg-amber-"], .memo-doc [class*="bg-sky-"] {
    -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}`;

export default function MemoPage() {
  const app = useApp();
  const ui = (app as unknown as { lang?: string }).lang === "bn" ? "bn" : "en";
  const t = TXT[ui];
  const { id } = useParams<{ id: string }>();
  const [memo, setMemo] = useState<MemoResponse | null>(null);
  const [bnText, setBnText] = useState<string | null>(null);
  const [docLang, setDocLang] = useState<"en" | "bn">("en");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [translating, setTranslating] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    getMemo(id)
      .then((m) => { if (alive) { setMemo(m); if (m?.markdown_bn) setBnText(m.markdown_bn); } })
      .catch((e: unknown) => { if (alive) setError(e instanceof Error ? e.message : "Could not load the memo."); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [id]);

  async function draft() {
    setBusy(true); setError("");
    try { setMemo(await draftMemo(id)); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not draft the memo."); }
    finally { setBusy(false); }
  }

  async function ensureBn(): Promise<boolean> {
    if (bnText) return true;
    setTranslating(true); setError("");
    try { setBnText((await translateMemo(id)).markdown); return true; }
    catch (e) { setError(e instanceof Error ? e.message : "Could not translate the memo."); return false; }
    finally { setTranslating(false); }
  }

  async function show(lang: "en" | "bn") {
    if (lang === "bn" && !(await ensureBn())) return;
    setDocLang(lang);
  }

  async function pdf(lang: "en" | "bn") {
    if (lang === "bn" && !(await ensureBn())) return;
    setDocLang(lang);
    const title = document.title;
    document.title = `Nirikkha-legal-memo-${id.slice(0, 8)}-${lang}`;
    setTimeout(() => { window.print(); document.title = title; }, 150);
  }

  function downloadMd() {
    const text = docLang === "bn" && bnText ? bnText : memo?.markdown;
    if (!text) return;
    const url = URL.createObjectURL(new Blob([text], { type: "text/markdown;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url; a.download = `nirikkha-legal-memo-${id.slice(0, 8)}-${docLang}.md`; a.click();
    URL.revokeObjectURL(url);
  }

  const d = DOC[docLang];
  const text = docLang === "bn" && bnText ? bnText : memo?.markdown ?? "";
  const today = new Date().toLocaleDateString(docLang === "bn" ? "bn-BD" : "en-GB", { day: "numeric", month: "long", year: "numeric" });

  return (
    <main className="mx-auto w-full max-w-4xl px-4 py-8 sm:py-10">
      <style>{PRINT_CSS}</style>
      <Link href={`/report/${id}`} className="text-sm opacity-70 hover:opacity-100">← {t.back}</Link>
      <p className="mt-6 text-xs font-semibold uppercase tracking-[0.2em] text-amber-500">{t.kicker}</p>
      <h1 className="mt-2 text-2xl font-bold sm:text-3xl">{t.title}</h1>

      {error && <div className="mt-5"><Alert>{error}</Alert></div>}

      {loading ? (
        <Loader />
      ) : !memo ? (
        <div className="mt-8 rounded-2xl border border-slate-500/20 bg-slate-500/[0.04] p-8 text-center">
          <p className="opacity-80">{t.none}</p>
          <Button className="mt-5" loading={busy} onClick={draft}>{busy ? t.drafting : t.draft}</Button>
        </div>
      ) : (
        <>
          <div className="mt-6 flex flex-wrap items-center gap-2">
            <span className="text-xs opacity-60">{t.view}:</span>
            {(["en", "bn"] as const).map((l) => (
              <button key={l} type="button" onClick={() => show(l)}
                className={`rounded-full border px-3 py-1 text-sm ${docLang === l ? "border-amber-500 bg-amber-500/15 text-amber-500" : "border-slate-500/30 opacity-70"}`}>
                {l === "en" ? "English" : "বাংলা"}
              </button>
            ))}
            <span className="mx-2 h-5 w-px bg-slate-500/30" />
            <Button onClick={() => pdf("en")}>⬇ {t.pdfEn}</Button>
            <Button variant="ghost" loading={translating} onClick={() => pdf("bn")}>⬇ {t.pdfBn}</Button>
            <Button variant="ghost" onClick={downloadMd}>{t.md}</Button>
          </div>
          {translating && <p className="mt-2 text-xs opacity-70">{t.translating}</p>}

          <article className="memo-doc mt-6 overflow-hidden rounded-2xl border border-slate-300 bg-white text-slate-800 shadow-xl shadow-black/20" lang={docLang}>
            <div className="memo-band flex items-center justify-between gap-4 bg-slate-900 px-6 py-4 text-white sm:px-10">
              <div className="flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-400 text-lg font-black text-slate-900">N</span>
                <div>
                  <p className="text-sm font-bold tracking-wide">NIRIKKHA · নিরীক্ষা</p>
                  <p className="text-[11px] text-slate-300">{d.band}</p>
                </div>
              </div>
              <div className="text-right text-[11px] text-slate-300">
                <p>{today}</p>
                <p>{d.run} {id.slice(0, 8)}</p>
              </div>
            </div>
            <div className="memo-body px-6 py-8 sm:px-10">
              <div className="mb-6 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">⚖ {TXT[docLang].notice}</div>
              <Markdown text={text} />
              <div className="mt-10 flex flex-wrap justify-between gap-2 border-t border-slate-200 pt-3 text-[11px] text-slate-500">
                <span>{d.footer}</span>
                <span>{d.draft}</span>
              </div>
            </div>
          </article>
        </>
      )}
    </main>
  );
}