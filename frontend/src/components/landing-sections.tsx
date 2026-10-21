"use client";

import Link from "next/link";

import { useApp } from "./providers";

const TXT = {
  en: {
    whatK: "What you can do", whatT: "One evidence-first workspace for governance due diligence",
    features: [
      { href: "/crash-test", icon: "🧪", t: "Crash-Test a decision", d: "Type the decision you are about to make. Nirikkha reads the 10-K and proxy, runs four investigations and scores governance health." },
      { href: "/reports", icon: "📑", t: "Reports and legal memo", d: "Every finding links to the filing, page and passage. Turn a report into a legal memo in English or Bengali." },
      { href: "/replay", icon: "⏪", t: "First Warning Sign Replay", d: "See the test on a real failure: Silicon Valley Bank, with evidence frozen before the collapse." },
      { href: "/graph", icon: "🕸️", t: "Relationship graph", d: "Directors, officers, committees and outside boards, with shared organizations highlighted for conflict-of-interest review." },
      { href: "/radar", icon: "📡", t: "Regulatory Change Radar", d: "New SEC rules and new filings become prioritised alerts. A person approves or rejects each one." },
      { href: "/pricing", icon: "🌐", t: "Bengali and English", d: "The whole interface works in both languages, from the report to the memo." },
    ],
    howK: "How it works", howT: "From public filings to a verifiable answer",
    steps: [
      { t: "Collect", d: "Form 10-K and proxy statements are fetched from SEC EDGAR and split into cited passages." },
      { t: "Ask", d: "You describe a decision. Personal data is removed and the request is safety-checked." },
      { t: "Investigate", d: "AI agents search the evidence, a rule engine tests SEC disclosure rules, and a second model checks every AI finding." },
      { t: "Decide", d: "A health score with risk severity and evidence confidence kept apart. Missing evidence is shown, never hidden." },
    ],
    proofK: "Proof, not promises", proofT: "Tested on a real bank failure",
    proofSub: "We froze SVB's public filings three days before it failed, ran Nirikkha on that alone, and compared the result with what the Federal Reserve later found.",
    stats: [
      { v: "3 days", l: "before the failure, evidence frozen" },
      { v: "5 of 5", l: "knowable warning signs raised (2 flagged, 3 questioned)" },
      { v: "0", l: "citations from after the freeze" },
      { v: "87 vs 68", l: "control company (Apple) vs SVB health score" },
    ],
    proofCta: "Open the Replay",
    trustK: "Built responsibly", trustT: "An AI that knows when it does not know",
    trust: [
      { t: "Every claim cited", d: "Findings link to the source document, page and passage." },
      { t: "Insufficient evidence is visible", d: "Gaps are listed, never scored as low risk." },
      { t: "Humans decide", d: "Uncertain findings and Radar alerts wait for human review." },
      { t: "Private by default", d: "Personal data is removed before any model sees a request." },
    ],
    whoK: "Who it is for",
    who: ["Investment analysts and funds", "Banks: credit and KYC teams", "Corporate compliance and internal audit", "Governance advisory and audit firms"],
    ctaT: "Test the evidence before the decision.", ctaRun: "Run a Crash-Test", ctaDemo: "Try the demo",
  },
  bn: {
    whatK: "আপনি যা করতে পারবেন", whatT: "গভর্ন্যান্স যাচাইয়ের জন্য প্রমাণভিত্তিক একটি ওয়ার্কস্পেস",
    features: [
      { href: "/crash-test", icon: "🧪", t: "সিদ্ধান্তের ক্র্যাশ-টেস্ট", d: "যে সিদ্ধান্ত নিতে যাচ্ছেন তা লিখুন। Nirikkha 10-K আর প্রক্সি পড়ে, চারটি অনুসন্ধান চালায় আর গভর্ন্যান্স হেলথ স্কোর দেয়।" },
      { href: "/reports", icon: "📑", t: "রিপোর্ট ও লিগ্যাল মেমো", d: "প্রতিটি ফাইন্ডিং ফাইলিং, পৃষ্ঠা আর অনুচ্ছেদের সাথে যুক্ত। রিপোর্ট থেকে বাংলা বা ইংরেজিতে লিগ্যাল মেমো তৈরি করুন।" },
      { href: "/replay", icon: "⏪", t: "ফার্স্ট ওয়ার্নিং সাইন রিপ্লে", d: "আসল ব্যর্থতায় পরীক্ষা দেখুন: সিলিকন ভ্যালি ব্যাংক, পতনের আগে প্রমাণ ফ্রিজ করে।" },
      { href: "/graph", icon: "🕸️", t: "সম্পর্কের জাল", d: "পরিচালক, কর্মকর্তা, কমিটি আর বাইরের বোর্ড; যৌথ প্রতিষ্ঠানগুলো স্বার্থের সংঘাত যাচাইয়ের জন্য চিহ্নিত।" },
      { href: "/radar", icon: "📡", t: "রেগুলেটরি চেঞ্জ রাডার", d: "নতুন SEC নিয়ম আর নতুন ফাইলিং অগ্রাধিকারসহ সতর্কবার্তা হয়; প্রতিটি একজন মানুষ অনুমোদন বা প্রত্যাখ্যান করেন।" },
      { href: "/pricing", icon: "🌐", t: "বাংলা ও ইংরেজি", d: "পুরো ইন্টারফেস দুই ভাষাতেই চলে, রিপোর্ট থেকে মেমো পর্যন্ত।" },
    ],
    howK: "কীভাবে কাজ করে", howT: "প্রকাশ্য ফাইলিং থেকে যাচাইযোগ্য উত্তর",
    steps: [
      { t: "সংগ্রহ", d: "SEC EDGAR থেকে Form 10-K আর প্রক্সি স্টেটমেন্ট এনে উদ্ধৃতিযোগ্য অনুচ্ছেদে ভাগ করা হয়।" },
      { t: "প্রশ্ন", d: "আপনি একটি সিদ্ধান্ত লেখেন। ব্যক্তিগত তথ্য মুছে ফেলা হয় আর অনুরোধটি নিরাপত্তা-যাচাই হয়।" },
      { t: "অনুসন্ধান", d: "AI এজেন্ট প্রমাণ খোঁজে, রুল ইঞ্জিন SEC-এর disclosure নিয়ম পরীক্ষা করে, আর দ্বিতীয় একটি মডেল প্রতিটি AI ফাইন্ডিং যাচাই করে।" },
      { t: "সিদ্ধান্ত", d: "হেলথ স্কোর, যেখানে ঝুঁকির মাত্রা আর প্রমাণের আস্থা আলাদা। ঘাটতি দেখানো হয়, কখনো লুকানো হয় না।" },
    ],
    proofK: "প্রতিশ্রুতি নয়, প্রমাণ", proofT: "আসল একটি ব্যাংক ব্যর্থতায় পরীক্ষিত",
    proofSub: "ব্যর্থ হওয়ার তিন দিন আগে SVB-এর প্রকাশ্য ফাইলিং ফ্রিজ করে শুধু সেটুকু দিয়ে Nirikkha চালানো হয়েছে, তারপর ফেডারেল রিজার্ভ পরে যা পেয়েছে তার সাথে মেলানো হয়েছে।",
    stats: [
      { v: "৩ দিন", l: "ব্যর্থতার আগে প্রমাণ ফ্রিজ" },
      { v: "৫টির ৫টি", l: "জানার মতো সতর্কসংকেত উঠেছে (২টি চিহ্নিত, ৩টি প্রশ্ন)" },
      { v: "০", l: "ফ্রিজের পরের কোনো উদ্ধৃতি" },
      { v: "৮৭ বনাম ৬৮", l: "কন্ট্রোল কোম্পানি (Apple) বনাম SVB-এর হেলথ স্কোর" },
    ],
    proofCta: "রিপ্লে খুলুন",
    trustK: "দায়িত্বশীলভাবে তৈরি", trustT: "এমন AI, যে জানে কখন সে জানে না",
    trust: [
      { t: "প্রতিটি দাবির উৎস", d: "ফাইন্ডিং মূল নথি, পৃষ্ঠা আর অনুচ্ছেদের সাথে যুক্ত।" },
      { t: "অপর্যাপ্ত প্রমাণ দৃশ্যমান", d: "ঘাটতি তালিকায় থাকে, কখনো কম ঝুঁকি বলে গোনা হয় না।" },
      { t: "সিদ্ধান্ত মানুষের", d: "অনিশ্চিত ফাইন্ডিং আর রাডারের সতর্কবার্তা মানুষের পর্যালোচনার অপেক্ষায় থাকে।" },
      { t: "ডিফল্টভাবে গোপন", d: "কোনো মডেল দেখার আগেই ব্যক্তিগত তথ্য মুছে ফেলা হয়।" },
    ],
    whoK: "কাদের জন্য",
    who: ["ইনভেস্টমেন্ট অ্যানালিস্ট ও ফান্ড", "ব্যাংক: ক্রেডিট ও KYC টিম", "কর্পোরেট কমপ্লায়েন্স ও ইন্টারনাল অডিট", "গভর্ন্যান্স অ্যাডভাইজরি ও অডিট ফার্ম"],
    ctaT: "সিদ্ধান্তের আগে প্রমাণ পরীক্ষা করুন।", ctaRun: "ক্র্যাশ-টেস্ট চালান", ctaDemo: "ডেমো দেখুন",
  },
};

const panel = "rounded-2xl border border-slate-500/20 bg-slate-500/[0.04]";

function Kicker({ children }: { children: string }) {
  return <p className="text-xs font-semibold uppercase tracking-[0.2em] text-amber-500">{children}</p>;
}

export function LandingSections() {
  const app = useApp();
  const t = TXT[(app as unknown as { lang?: string }).lang === "bn" ? "bn" : "en"];
  return (
    <div className="mx-auto w-full max-w-6xl space-y-24 px-4 pb-24 pt-8 sm:px-6">
      <section>
        <Kicker>{t.whatK}</Kicker>
        <h2 className="mt-2 max-w-3xl text-2xl font-bold sm:text-3xl">{t.whatT}</h2>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {t.features.map((f) => (
            <div key={f.href + f.t} className={`${panel} p-6`}>
              <span className="text-2xl" aria-hidden>{f.icon}</span>
              <h3 className="mt-3 text-lg font-semibold">{f.t}</h3>
              <p className="mt-2 text-sm leading-relaxed opacity-75">{f.d}</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <Kicker>{t.howK}</Kicker>
        <h2 className="mt-2 text-2xl font-bold sm:text-3xl">{t.howT}</h2>
        <ol className="mt-8 grid gap-4 md:grid-cols-4">
          {t.steps.map((s, i) => (
            <li key={s.t} className={`${panel} relative p-6`}>
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-amber-500 font-bold text-slate-900">{i + 1}</span>
              <h3 className="mt-4 font-semibold">{s.t}</h3>
              <p className="mt-2 text-sm leading-relaxed opacity-75">{s.d}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="overflow-hidden rounded-3xl border border-slate-500/20 bg-gradient-to-br from-emerald-500/[0.08] via-transparent to-rose-500/[0.10] p-6 sm:p-10">
        <Kicker>{t.proofK}</Kicker>
        <h2 className="mt-2 text-2xl font-bold sm:text-3xl">{t.proofT}</h2>
        <p className="mt-3 max-w-3xl text-sm leading-relaxed opacity-80 sm:text-base">{t.proofSub}</p>
        <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {t.stats.map((s) => (
            <div key={s.l} className="rounded-2xl border border-slate-500/25 bg-slate-500/[0.06] p-5">
              <p className="text-3xl font-bold text-amber-500">{s.v}</p>
              <p className="mt-2 text-sm opacity-75">{s.l}</p>
            </div>
          ))}
        </div>
        <Link href="/replay" className="mt-8 inline-block rounded-lg bg-amber-500 px-5 py-3 text-sm font-semibold text-slate-900 hover:bg-amber-400">{t.proofCta} →</Link>
      </section>

      <section className="grid gap-10 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div>
          <Kicker>{t.trustK}</Kicker>
          <h2 className="mt-2 text-2xl font-bold sm:text-3xl">{t.trustT}</h2>
          <ul className="mt-6 grid gap-3 sm:grid-cols-2">
            {t.trust.map((x) => (
              <li key={x.t} className={`${panel} p-5`}>
                <p className="font-semibold"><span className="text-emerald-500">✓</span> {x.t}</p>
                <p className="mt-1 text-sm opacity-75">{x.d}</p>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <Kicker>{t.whoK}</Kicker>
          <ul className="mt-6 space-y-3">
            {t.who.map((w) => (
              <li key={w} className={`${panel} flex items-center gap-3 px-5 py-4 text-sm`}><span className="text-amber-500">●</span>{w}</li>
            ))}
          </ul>
        </div>
      </section>

      <section className={`${panel} flex flex-col items-start justify-between gap-6 p-8 sm:flex-row sm:items-center sm:p-10`}>
        <h2 className="text-2xl font-bold sm:text-3xl">{t.ctaT}</h2>
        <div className="flex flex-wrap gap-3">
          <Link href="/crash-test" className="rounded-lg bg-amber-500 px-5 py-3 text-sm font-semibold text-slate-900 hover:bg-amber-400">{t.ctaRun}</Link>
          <Link href="/login?demo=1&next=/crash-test" className="rounded-lg border border-amber-500/60 px-5 py-3 text-sm font-semibold text-amber-500 hover:bg-amber-500/10">{t.ctaDemo}</Link>
        </div>
      </section>
    </div>
  );
}