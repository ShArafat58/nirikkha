"use client";

// 404 page. Layout and illustration generated with v0 (Vercel):
// https://v0.app/sharafat58s-projects/chat/ufJXysDLYiq — adapted to the Nirikkha theme tokens and EN/BN text.
import Link from "next/link";
import { useApp } from "../components/providers";

const TEXT = {
  en: {
    label: "Case file 404",
    title: "This page is not in the evidence.",
    body: "The link may be old, or the page was moved. Nothing here is a finding.",
    primary: "Go to Crash-Test",
    secondary: "Back to home",
    help: "Need help? Ask the Nirikkha Guide (bottom right).",
    aria: "A magnifying glass examining a page",
  },
  bn: {
    label: "কেস ফাইল ৪০৪",
    title: "এই পাতাটি প্রমাণের মধ্যে নেই।",
    body: "লিংকটি পুরোনো হতে পারে, অথবা পাতাটি সরানো হয়েছে। এখানে কোনো ফলাফল নেই।",
    primary: "ক্র্যাশ-টেস্টে যান",
    secondary: "হোমে ফিরে যান",
    help: "সাহায্য লাগবে? নিরীক্ষা গাইডকে জিজ্ঞেস করুন (নিচে ডানে)।",
    aria: "একটি পাতার উপর ম্যাগনিফাইং গ্লাস",
  },
} as const;

export default function NotFound() {
  const { lang } = useApp();
  const tx = TEXT[lang === "bn" ? "bn" : "en"];

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-bg px-6 py-12 text-text">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-40"
      >
        <div className="absolute left-1/2 top-1/4 h-px w-2/3 -translate-x-1/2 bg-gradient-to-r from-transparent via-accent to-transparent" />
        <div className="absolute bottom-1/4 left-1/2 h-px w-2/3 -translate-x-1/2 bg-gradient-to-r from-transparent via-accent to-transparent" />
      </div>

      <section className="relative flex w-full max-w-2xl flex-col items-center text-center">
        <div
          className="mb-8 motion-safe:animate-[nf-float_5s_ease-in-out_infinite] motion-reduce:animate-none"
          aria-label={tx.aria}
          role="img"
        >
          <svg
            className="h-44 w-72 sm:h-56 sm:w-96"
            viewBox="0 0 384 224"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <text
              x="192"
              y="166"
              textAnchor="middle"
              className="fill-text font-sans text-[148px] font-bold tracking-[-0.08em]"
            >
              404
            </text>
            <g transform="translate(118 22) rotate(-18 54 54)">
              <circle
                cx="54"
                cy="54"
                r="39"
                className="fill-surface stroke-accent"
                strokeWidth="7"
              />
              <circle
                cx="54"
                cy="54"
                r="25"
                className="fill-bg stroke-accent"
                strokeWidth="2"
                opacity="0.7"
              />
              <path
                d="M82 82L111 111"
                className="stroke-accent"
                strokeWidth="11"
                strokeLinecap="round"
              />
              <path
                d="M82 82L111 111"
                className="stroke-text"
                strokeWidth="3"
                strokeLinecap="round"
                opacity="0.55"
              />
            </g>
            <path
              d="M221 70H284M221 88H270M221 106H278"
              className="stroke-accent"
              strokeWidth="3"
              strokeLinecap="round"
              opacity="0.8"
            />
            <path
              d="M218 54C218 48.477 222.477 44 228 44H291C296.523 44 301 48.477 301 54V127C301 132.523 296.523 137 291 137H228C222.477 137 218 132.523 218 127V54Z"
              className="stroke-muted"
              strokeWidth="2"
              opacity="0.45"
            />
          </svg>
        </div>

        <p className="mb-4 text-xs font-semibold uppercase tracking-[0.28em] text-accent">
          {tx.label}
        </p>
        <h1 className="max-w-xl text-balance text-3xl font-semibold tracking-tight sm:text-5xl">
          {tx.title}
        </h1>
        <p className="mt-5 max-w-lg text-pretty text-base leading-7 text-muted sm:text-lg">
          {tx.body}
        </p>

        <div className="mt-9 flex w-full flex-col items-stretch justify-center gap-3 sm:w-auto sm:flex-row">
          <Link
            href="/crash-test"
            className="inline-flex min-h-11 items-center justify-center rounded-md bg-accent px-6 py-3 text-sm font-semibold text-accent-contrast shadow-lg shadow-accent/10 transition-colors hover:bg-accent/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
          >
            {tx.primary}
          </Link>
          <Link
            href="/"
            className="inline-flex min-h-11 items-center justify-center rounded-md border border-accent px-6 py-3 text-sm font-semibold text-accent transition-colors hover:bg-accent/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
          >
            {tx.secondary}
          </Link>
        </div>

        <p className="mt-16 text-sm text-muted">{tx.help}</p>
      </section>

      <style>{`@keyframes nf-float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }`}</style>
    </main>
  );
}
