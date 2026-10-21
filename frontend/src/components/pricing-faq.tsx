"use client";

// Pricing FAQ accordion generated with Claude Artifacts: https://claude.ai/artifact/JYA7TcanCocrbDogeWNL28
// Used as generated; the wrapper passes Bengali text.
import { useId } from "react";

export type FaqItem = { q: string; a: string };

export interface PricingFaqProps {
  title?: string;
  items?: FaqItem[];
}

const DEFAULT_ITEMS: FaqItem[] = [
  {
    q: "Is there a free plan?",
    a: "Yes. The Free plan includes 3 Crash-Tests a month with a short report and evidence links.",
  },
  {
    q: "Can I pay now?",
    a: "Not yet. The prototype has no live payment. Use Start Free, or Request a Pilot for team and enterprise use.",
  },
  {
    q: "What is a Crash-Test?",
    a: "One analysis of a company for a specific decision: four investigations, a rule check, a reliability check and an evidence-linked report.",
  },
  {
    q: "What happens if I need more Crash-Tests?",
    a: "Extra Crash-Tests are $19 each. A Deep Investigation Report with multi-year analysis is $199.",
  },
  {
    q: "Can confidential documents stay on our own servers?",
    a: "Yes, in the Enterprise plan: approved private documents and deployment on your own servers, so data does not leave your environment.",
  },
  {
    q: "Is this legal or investment advice?",
    a: "No. Nirikkha shows evidence and open questions for your team to verify.",
  },
];

function ChevronIcon() {
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-5 w-5 shrink-0 text-muted transition-transform duration-300 ease-out group-open:rotate-180 group-open:text-accent motion-reduce:transition-none"
    >
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

export default function PricingFaq({
  title = "Questions about plans",
  items = DEFAULT_ITEMS,
}: PricingFaqProps) {
  const headingId = useId();

  return (
    <section
      aria-labelledby={headingId}
      className="mx-auto w-full max-w-3xl text-text"
    >
      <h2
        id={headingId}
        className="text-2xl font-semibold tracking-tight text-text [text-wrap:balance] sm:text-3xl"
      >
        {title}
      </h2>

      <ul role="list" className="mt-8 flex flex-col gap-3">
        {items.map((item, i) => (
          <li key={`${i}-${item.q}`}>
            <details className="group rounded-xl border border-border bg-surface transition-colors duration-300 open:border-accent motion-reduce:transition-none">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 rounded-xl px-5 py-4 text-left text-base font-medium text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 [&::-webkit-details-marker]:hidden">
                <span className="min-w-0">{item.q}</span>
                <ChevronIcon />
              </summary>
              <div className="px-5 pb-5 text-[0.95rem] leading-relaxed text-muted">
                <p className="max-w-prose">{item.a}</p>
              </div>
            </details>
          </li>
        ))}
      </ul>
    </section>
  );
}
