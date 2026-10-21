"use client";

// Glossary generated with Gemini Canvas: https://share.gemini.google/OhgvfuAyzWSh
// Change on review: the hard-coded English subtitle became a prop so Bengali works.

export interface GlossaryItem {
  term: string;
  text: string;
  tone: "pass" | "gap" | "fail" | "insufficient" | "info";
}

export interface ResultGlossaryProps {
  title?: string;
  subtitle?: string;
  items?: GlossaryItem[];
}

const defaultItems: GlossaryItem[] = [
  {
    term: "Pass",
    text: "The available evidence meets the rule's test.",
    tone: "pass",
  },
  {
    term: "Potential Gap",
    text: "The evidence suggests a possible weakness that a person should review. It is not a finding of wrongdoing.",
    tone: "gap",
  },
  {
    term: "Fail",
    text: "Sufficient, applicable evidence shows the requirement was not met.",
    tone: "fail",
  },
  {
    term: "Insufficient Evidence",
    text: "Public filings do not contain enough to reach a reliable conclusion. It is never counted as low risk.",
    tone: "insufficient",
  },
  {
    term: "Risk Severity vs Evidence Confidence",
    text: "Severity is how serious an issue would be. Confidence is how strong the evidence is. They are shown separately.",
    tone: "info",
  },
  {
    term: "Not applicable",
    text: "The rule does not apply to this company, for example a bank-only practice for a technology company.",
    tone: "info",
  },
  {
    term: "Reliability Sentinel",
    text: "A second model checks every AI finding against its cited passage and sends doubtful ones to human review.",
    tone: "info",
  },
  {
    term: "Health Score",
    text: "A 0 to 100 summary. Every deduction is listed with the finding that caused it.",
    tone: "info",
  },
];

function getDotClass(tone: GlossaryItem["tone"]): string {
  switch (tone) {
    case "pass":
      return "bg-rule-pass";
    case "gap":
      return "bg-rule-gap";
    case "fail":
      return "bg-rule-fail";
    case "insufficient":
      return "bg-rule-insufficient";
    default:
      return "bg-accent";
  }
}

function getStatusIcon(tone: GlossaryItem["tone"]) {
  const dotClass = getDotClass(tone);
  if (tone === "pass" || tone === "fail") {
    return (
      <span
        className={`mt-1 inline-flex h-3 w-3 flex-shrink-0 items-center justify-center rounded-full ${dotClass}`}
      >
        <span
          className={`${tone === "pass" ? "h-1.5 w-1.5" : "h-1 w-1"} rounded-full bg-surface`}
        />
      </span>
    );
  }
  if (tone === "gap" || tone === "insufficient") {
    return (
      <span
        className={`mt-1 inline-block h-3 w-3 flex-shrink-0 rounded-sm ${dotClass}`}
      />
    );
  }
  return (
    <span
      className={`mt-1 inline-block h-3 w-3 flex-shrink-0 rounded-full ${dotClass}`}
    />
  );
}

export default function ResultGlossary({
  title = "How to read a report",
  subtitle = "Reference guide for the terms and result types used in every Nirikkha report.",
  items = defaultItems,
}: ResultGlossaryProps) {
  return (
    <section className="w-full rounded-xl border border-border bg-surface p-6 text-text shadow-sm md:p-8">
      <div className="mb-6">
        <h2 className="text-2xl font-bold tracking-tight text-text">{title}</h2>
        <p className="mt-1 text-sm text-muted">{subtitle}</p>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 md:gap-6">
        {items.map((item, index) => (
          <div
            key={index}
            className="flex items-start rounded-lg border border-border bg-surface p-4 transition-colors hover:border-accent"
          >
            <div className="mr-3 pt-1">{getStatusIcon(item.tone)}</div>
            <div className="flex-1">
              <h3 className="mb-1 text-base font-semibold text-text">
                {item.term}
              </h3>
              <p className="text-sm leading-relaxed text-muted">{item.text}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
