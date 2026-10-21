// Empty state for "My reports". Generated with Bolt.new: https://bolt.new/p/72252449
// Reviewed changes: fixed the steps merge (Bolt spread an array into an object, which broke .map),
// replaced the missing animate-fade-in utility with a local keyframe, used a standard width class.

type ReportsEmptyStateLabels = {
  title: string;
  body: string;
  steps: [string, string, string];
  primary: string;
  secondary: string;
};

type ReportsEmptyStateProps = {
  labels?: Partial<ReportsEmptyStateLabels>;
};

const DEFAULT_LABELS: ReportsEmptyStateLabels = {
  title: "No reports yet",
  body: "Run your first Crash-Test: pick a company, describe your decision, and Nirikkha will collect the evidence.",
  steps: ["Pick a company", "Describe the decision", "Read the evidence"],
  primary: "Start a Crash-Test",
  secondary: "See a public demo",
};

export default function ReportsEmptyState({ labels }: ReportsEmptyStateProps) {
  const merged: ReportsEmptyStateLabels = {
    ...DEFAULT_LABELS,
    ...labels,
    steps: labels?.steps ?? DEFAULT_LABELS.steps,
  };

  return (
    <section className="rounded-2xl border border-border bg-surface p-8 motion-safe:animate-[res-fade_0.5s_ease-out] sm:p-12">
      <div className="mx-auto flex max-w-xl flex-col items-center text-center">
        <EmptyFolderIllustration />

        <h2 className="mt-6 text-2xl font-semibold tracking-tight text-text">
          {merged.title}
        </h2>
        <p className="mt-3 leading-relaxed text-muted">{merged.body}</p>

        <ol className="mt-8 grid w-full gap-3 sm:grid-cols-3 sm:gap-4">
          {merged.steps.map((step, i) => (
            <li
              key={i}
              className="flex items-center gap-3 rounded-lg border border-border bg-bg px-4 py-3 text-left"
            >
              <span
                aria-hidden="true"
                className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-accent text-sm font-semibold text-accent"
              >
                {i + 1}
              </span>
              <span className="text-sm leading-snug text-text">{step}</span>
            </li>
          ))}
        </ol>

        <div className="mt-8 flex flex-col items-center gap-4 sm:flex-row">
          <a
            href="/crash-test"
            className="inline-flex items-center justify-center rounded-lg bg-accent px-6 py-3 text-sm font-semibold text-accent-contrast transition hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
          >
            {merged.primary}
          </a>
          <a
            href="/reports#featured"
            className="rounded text-sm font-medium text-accent underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            {merged.secondary}
          </a>
        </div>
      </div>
      <style>{`@keyframes res-fade { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }`}</style>
    </section>
  );
}

function EmptyFolderIllustration() {
  return (
    <svg
      role="img"
      aria-label="An empty folder with a magnifying glass, awaiting evidence"
      viewBox="0 0 120 100"
      className="h-28 w-36 text-muted"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path
        d="M14 30 a4 4 0 0 1 4-4 h18 l8 8 h44 a4 4 0 0 1 4 4 v2 H14 z"
        className="fill-surface"
      />
      <path
        d="M14 40 h78 a4 4 0 0 1 4 4 v28 a4 4 0 0 1 -4 4 H18 a4 4 0 0 1 -4 -4 z"
        className="fill-bg"
      />
      <g strokeDasharray="1.5 3" opacity="0.55">
        <path d="M24 54 h28" />
        <path d="M24 62 h22" />
        <path d="M24 70 h26" />
      </g>
      <g transform="translate(70 48)">
        <circle cx="10" cy="10" r="9" className="stroke-accent" />
        <path d="M16.5 16.5 l8 8" className="stroke-accent" strokeWidth="2.5" />
        <path d="M6 10 h8" className="stroke-accent" opacity="0.5" />
      </g>
    </svg>
  );
}

export const EMPTY_LABELS_BN: ReportsEmptyStateLabels = {
  title: "এখনো কোনো রিপোর্ট নেই",
  body: "প্রথম ক্র্যাশ-টেস্ট চালান: একটি কোম্পানি বেছে নিন, আপনার সিদ্ধান্ত লিখুন, নিরীক্ষা প্রমাণ সংগ্রহ করবে।",
  steps: ["কোম্পানি বেছে নিন", "সিদ্ধান্ত লিখুন", "প্রমাণ পড়ুন"],
  primary: "ক্র্যাশ-টেস্ট শুরু করুন",
  secondary: "একটি প্রকাশ্য ডেমো দেখুন",
};
