"use client";

import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { useApp } from "./providers";
import { chatHelp, type HelpChatMessage } from "../lib/api";

type Message = {
  role: "user" | "assistant";
  content: string;
  source?: "llm" | "faq";
};

// Suggested questions based on the active route
const SUGGESTIONS: Record<string, { en: string[]; bn: string[] }> = {
  "/crash-test": {
    en: [
      "How do I run a Crash-Test?",
      "What is an Evidence Freeze Date?",
      "What should I write in the decision text?",
      "What are the 13 pipeline stages?",
    ],
    bn: [
      "ক্র্যাশ-টেস্ট কীভাবে শুরু করব?",
      "এভিডেন্স ফ্রিজ ডেট কী?",
      "সিদ্ধান্তের বক্সে কী লিখতে হবে?",
      "পাইপলাইনের ১৩টি ধাপ কী কী?",
    ],
  },
  "/reports": {
    en: [
      "How is the Health Score calculated?",
      "What does Insufficient Evidence mean?",
      "Explain Risk Severity vs Evidence Confidence",
      "How do I export a report or legal memo?",
    ],
    bn: [
      "গভর্ন্যান্স হেলথ স্কোর কীভাবে গণনা করা হয়?",
      "অপর্যাপ্ত প্রমাণ (Insufficient Evidence) কী?",
      "ঝুঁকির তীব্রতা এবং প্রমাণের বিশ্বাসযোগ্যতার পার্থক্য কী?",
      "রিপোর্ট বা লিগ্যাল মেমো কীভাবে এক্সপোর্ট করব?",
    ],
  },
  "/pricing": {
    en: [
      "What features come with Analyst Pro?",
      "How does the demo checkout work?",
      "How do I request an Enterprise pilot?",
      "What are the pay-per-report add-ons?",
    ],
    bn: [
      "এনালিস্ট প্রো প্ল্যানে কী কী সুবিধা আছে?",
      "ডেমো চেকআউট কীভাবে কাজ করে?",
      "এন্টারপ্রাইজ পাইলটের জন্য কীভাবে আবেদন করব?",
      "পে-পার-রিপোর্ট অ্যাড-অন কী?",
    ],
  },
  "/radar": {
    en: [
      "What do Approve and Reject do?",
      "What are the two alert streams?",
      "How is human review logged in the audit trail?",
      "How often is the radar updated?",
    ],
    bn: [
      "Approve এবং Reject বাটনের কাজ কী?",
      "রেডারের দুটি নোটিফিকেশন স্ট্রিম কী?",
      "হিউম্যান-ইন-দ্য-লুপ অডিট ট্রেইল কীভাবে কাজ করে?",
      "রেডার কত ঘন ঘন আপডেট হয়?",
    ],
  },
  "/replay": {
    en: [
      "What is the First Warning Sign Replay?",
      "What is the hindsight guard?",
      "Why is Silicon Valley Bank the case study?",
      "What does the VALID verdict mean?",
    ],
    bn: [
      "ফার্স্ট ওয়ার্নিং সাইন রিপ্লে কী?",
      "হাইন্ডসাইট গার্ড কীভাবে কাজ করে?",
      "সিলিকন ভ্যালি ব্যাংক কেস স্টাডি কেন বেছে নেওয়া হয়েছে?",
      "VALID রায়ের অর্থ কী?",
    ],
  },
  "/graph": {
    en: [
      "What does the Relationship Graph show?",
      "What is an interlock?",
      "Why does my graph appear empty?",
      "Which SEC regulation covers related parties?",
    ],
    bn: [
      "রিলেশনশিপ গ্রাফে কী কী নোড দেখা যায়?",
      "ইন্টারলক বা অভিন্ন বাইরের প্রতিষ্ঠান কী?",
      "গ্রাফ ফাঁকা দেখালে কী করব?",
      "সম্পর্কিত পক্ষ নিয়ে এসইসির নিয়ম কী?",
    ],
  },
  default: {
    en: [
      "What does Nirikkha do?",
      "What are the 4 parallel investigations?",
      "Is this legal or investment advice?",
      "How does Nirikkha verify SEC citations?",
    ],
    bn: [
      "নিরীক্ষা প্ল্যাটফর্মের মূল কাজ কী?",
      "৪টি সমান্তরাল তদন্ত কী কী?",
      "এটি কি কোনো আইনি বা বিনিয়োগ পরামর্শ?",
      "ফাইলিংয়ের উদ্ধৃতি কীভাবে যাচাই করা হয়?",
    ],
  },
};

export function HelpChat() {
  const { lang } = useApp();
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Suggested questions based on the route
  const pageRoute = Object.keys(SUGGESTIONS).find((route) => route !== "default" && pathname.startsWith(route)) ?? "default";
  const chips = SUGGESTIONS[pageRoute][lang] || SUGGESTIONS.default[lang];

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  const sendQuery = async (queryText: string) => {
    const text = queryText.trim();
    if (!text || busy) return;

    const userMessage: Message = { role: "user", content: text };
    const updated = [...messages, userMessage];
    setMessages(updated);
    setInput("");
    setBusy(true);

    try {
      const historyPayload: HelpChatMessage[] = updated.map((m) => ({
        role: m.role,
        content: m.content,
      }));
      const res = await chatHelp(historyPayload, lang, pathname);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.reply, source: res.source },
      ]);
    } catch {
      const fallback =
        lang === "bn"
          ? "দুঃখিত, সংযোগে সমস্যা হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।"
          : "Sorry, I could not reach the help service. Please try again in a moment.";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: fallback, source: "faq" },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
  };

  const isBn = lang === "bn";

  return (
    <>
      <style jsx global>{`
        @keyframes robot-float {
          0%,
          100% {
            transform: translateY(0);
          }
          50% {
            transform: translateY(-4px);
          }
        }
        @keyframes antenna-glow {
          0%,
          100% {
            filter: drop-shadow(0 0 2px var(--accent));
            opacity: 0.85;
          }
          50% {
            filter: drop-shadow(0 0 6px var(--accent));
            opacity: 1;
          }
        }
        @keyframes eye-blink {
          0%,
          92%,
          100% {
            transform: scaleY(1);
          }
          95% {
            transform: scaleY(0.1);
          }
        }
        .robot-animated {
          animation: robot-float 3.5s ease-in-out infinite;
        }
        .robot-antenna {
          animation: antenna-glow 2s ease-in-out infinite;
        }
        .robot-eye {
          transform-origin: center;
          animation: eye-blink 4s infinite;
        }
        @media (prefers-reduced-motion: reduce) {
          .robot-animated,
          .robot-antenna,
          .robot-eye {
            animation: none !important;
          }
        }
      `}</style>

      {/* Floating Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-label={isBn ? "সাহায্য চ্যাট খুলুন" : "Open help chat"}
        aria-expanded={isOpen}
        className="fixed bottom-5 right-5 z-50 flex h-14 w-14 items-center justify-center rounded-full border border-border bg-surface text-text shadow-xl shadow-black/30 transition-transform duration-200 hover:scale-105 hover:border-accent focus:outline-none focus:ring-2 focus:ring-accent"
      >
        <svg
          viewBox="0 0 40 40"
          className="robot-animated h-9 w-9 text-text"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Antenna */}
          <line
            x1="20"
            y1="4"
            x2="20"
            y2="10"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
          <circle
            cx="20"
            cy="4"
            r="3"
            fill="var(--accent)"
            className="robot-antenna"
          />

          {/* Head */}
          <rect
            x="7"
            y="10"
            width="26"
            height="20"
            rx="6"
            fill="var(--surface-2)"
            stroke="currentColor"
            strokeWidth="2.2"
          />

          {/* Visor / Eye display */}
          <rect
            x="11"
            y="14"
            width="18"
            height="9"
            rx="3.5"
            fill="var(--bg)"
          />

          {/* Eyes */}
          <circle
            cx="15.5"
            cy="18.5"
            r="2.2"
            fill="var(--accent)"
            className="robot-eye"
          />
          <circle
            cx="24.5"
            cy="18.5"
            r="2.2"
            fill="var(--accent)"
            className="robot-eye"
          />

          {/* Cheerful Mouth / Accent notch */}
          <path
            d="M16 26 Q20 28.5 24 26"
            stroke="var(--muted)"
            strokeWidth="2"
            strokeLinecap="round"
          />

          {/* Ear dials */}
          <rect x="4" y="16" width="3" height="8" rx="1.5" fill="var(--accent)" />
          <rect x="33" y="16" width="3" height="8" rx="1.5" fill="var(--accent)" />
        </svg>
      </button>

      {/* Chat Panel / Popover */}
      {isOpen && (
        <div
          role="dialog"
          aria-label={isBn ? "নিরীক্ষা গাইড হেল্প চ্যাট" : "Nirikkha Guide Help Chat"}
          className="fixed inset-x-0 bottom-0 z-50 flex h-[82vh] flex-col rounded-t-2xl border border-border bg-surface text-text shadow-2xl backdrop-blur-md sm:bottom-22 sm:left-auto sm:right-5 sm:h-[32rem] sm:w-[24rem] sm:rounded-2xl"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border bg-surface-2/60 px-4 py-3">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-surface border border-border">
                <svg viewBox="0 0 24 24" className="h-5 w-5 text-accent" fill="none" stroke="currentColor">
                  <circle cx="12" cy="12" r="9" strokeWidth="2" />
                  <circle cx="9" cy="10" r="1.5" fill="currentColor" />
                  <circle cx="15" cy="10" r="1.5" fill="currentColor" />
                  <path d="M9 15c1 1 3 1 4 0" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </div>
              <div>
                <h3 className="text-sm font-semibold leading-tight text-text">
                  {isBn ? "নিরীক্ষা গাইড" : "Nirikkha Guide"}
                </h3>
                <p className="text-[11px] text-muted leading-tight">
                  {isBn ? "প্রোডাক্ট অ্যাসিস্ট্যান্ট" : "Product Assistant"}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1">
              {messages.length > 0 && (
                <button
                  type="button"
                  onClick={clearChat}
                  title={isBn ? "চ্যাট মুছুন" : "Clear conversation"}
                  aria-label={isBn ? "চ্যাট মুছুন" : "Clear conversation"}
                  className="rounded-lg p-1.5 text-muted hover:bg-surface hover:text-text"
                >
                  <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                  </svg>
                </button>
              )}
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                aria-label={isBn ? "চ্যাট বন্ধ করুন" : "Close chat"}
                className="rounded-lg p-1.5 text-muted hover:bg-surface hover:text-text"
              >
                <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Messages & Chips Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3.5 text-xs sm:text-sm">
            {/* Greeting */}
            <div className="rounded-xl border border-border bg-surface-2/40 p-3 text-muted">
              <p className="font-medium text-text">
                {isBn
                  ? "নমস্কার! আমি নিরীক্ষা গাইড।"
                  : "Hello! I am Nirikkha Guide."}
              </p>
              <p className="mt-1 text-xs">
                {isBn
                  ? "প্ল্যাটফর্মের ফিচার, ক্র্যাশ-টেস্টের ফলাফল, হেলথ স্কোর বা যেকোনো প্রশ্ন করতে পারেন।"
                  : "Ask me anything about Nirikkha, how to run tests, interpreting scores, or fixing common issues."}
              </p>
            </div>

            {/* Suggested Question Chips */}
            {messages.length === 0 && (
              <div className="space-y-1.5 pt-1">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted">
                  {isBn ? "প্রস্তাবিত প্রশ্ন" : "Suggested questions"}
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {chips.map((chip, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => sendQuery(chip)}
                      className="rounded-full border border-border bg-surface-2/70 px-3 py-1.5 text-left text-xs font-medium text-text hover:border-accent hover:bg-surface transition-colors"
                    >
                      {chip}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Message Thread */}
            {messages.map((m, idx) => (
              <div
                key={idx}
                className={`flex flex-col ${
                  m.role === "user" ? "items-end" : "items-start"
                }`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 whitespace-pre-line text-xs sm:text-sm ${
                    m.role === "user"
                      ? "bg-accent text-accent-contrast font-medium rounded-tr-none"
                      : "bg-surface-2 border border-border text-text rounded-tl-none shadow-sm"
                  }`}
                >
                  {m.content}
                </div>
                {m.role === "assistant" && m.source && (
                  <span className="mt-1 text-[10px] text-muted uppercase tracking-wider px-1">
                    {m.source === "faq" ? (isBn ? "গাইড এফএকিউ" : "Guide FAQ") : (isBn ? "এআই সহকারী" : "AI Assistant")}
                  </span>
                )}
              </div>
            ))}

            {/* Typing Indicator */}
            {busy && (
              <div className="flex items-center gap-1.5 rounded-xl border border-border bg-surface-2 px-3 py-2 text-xs text-muted w-24">
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent [animation-delay:0.2s]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent [animation-delay:0.4s]" />
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input & Footer */}
          <div className="border-t border-border bg-surface px-3 py-2.5">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                sendQuery(input);
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                maxLength={1000}
                placeholder={
                  isBn
                    ? "প্রশ্ন লিখুন (যেমন: ক্র্যাশ-টেস্ট কীভাবে চালাব)..."
                    : "Ask about Nirikkha, features, results..."
                }
                className="flex-1 rounded-xl border border-border bg-surface-2 px-3 py-2 text-xs sm:text-sm text-text placeholder-muted focus:border-accent focus:outline-none"
              />
              <button
                type="submit"
                disabled={!input.trim() || busy}
                aria-label={isBn ? "বার্তা পাঠান" : "Send message"}
                className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent text-accent-contrast disabled:opacity-40 hover:opacity-90 transition-opacity"
              >
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.2">
                  <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </form>

            <p className="mt-2 text-[10px] text-muted text-center leading-tight">
              {isBn
                ? "উত্তরগুলো নিরীক্ষার হেল্প গাইড থেকে দেওয়া। ব্যক্তিগত বা গোপনীয় তথ্য শেয়ার করবেন না।"
                : "Answers come from Nirikkha's help guide. Do not share personal or confidential information."}
            </p>
          </div>
        </div>
      )}
    </>
  );
}
