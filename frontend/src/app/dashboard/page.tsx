"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useApp } from "../../components/providers";
import { useSession } from "../../components/session";
import { getMyCrashTests } from "../../lib/api";
import { getRadar } from "../../lib/radar";

const PLAN_NAMES: Record<string, string> = {
  free: "Free",
  analyst_pro: "Analyst Pro",
  team: "Team",
  enterprise: "Enterprise",
};

// Local EN/BN strings for the new dashboard sections (keeps i18n.ts unchanged).
const L = {
  en: {
    sub: "Your governance evidence workspace",
    runs: "My Crash-Tests",
    avg: "Average Health Score",
    done: "Completed reports",
    radar: "Radar alerts to review",
    recent: "Recent Crash-Tests",
    viewAll: "View all reports",
    empty: "No Crash-Tests yet. Start one, or open a featured demo.",
    open: "Open",
    quick: "Explore Nirikkha",
    featured: "Featured demos",
    featuredSub: "Real public SEC filings, ready to open",
    status: {
      queued: "Queued",
      running: "Running",
      done: "Done",
      failed: "Failed",
      blocked: "Blocked",
    } as Record<string, string>,
    actions: [
      {
        href: "/crash-test",
        title: "New Crash-Test",
        desc: "Test a decision against a company's filings",
      },
      {
        href: "/replay",
        title: "SVB Replay",
        desc: "Warning signs found before March 2023",
      },
      {
        href: "/graph",
        title: "Relationship graph",
        desc: "Directors, committees, interlocks",
      },
      {
        href: "/radar",
        title: "Regulatory Radar",
        desc: "Approve or reject rule-change alerts",
      },
      {
        href: "/reports",
        title: "Reports",
        desc: "All Crash-Test reports and legal memos",
      },
      {
        href: "/docs",
        title: "Docs & status",
        desc: "Architecture, method, live status",
      },
    ],
    demos: [
      {
        name: "Silicon Valley Bank",
        note: "Frozen 7 Mar 2023 · Replay case",
        score: 68,
      },
      { name: "Apple Inc.", note: "Healthy-company control", score: 85 },
      {
        name: "Apple Inc. · Private",
        note: "All AI on local models",
        score: 94,
      },
    ],
  },
  bn: {
    sub: "আপনার গভর্নেন্স প্রমাণ যাচাইয়ের জায়গা",
    runs: "আমার ক্র্যাশ-টেস্ট",
    avg: "গড় হেলথ স্কোর",
    done: "সম্পন্ন রিপোর্ট",
    radar: "পর্যালোচনার রাডার অ্যালার্ট",
    recent: "সাম্প্রতিক ক্র্যাশ-টেস্ট",
    viewAll: "সব রিপোর্ট দেখুন",
    empty: "এখনো কোনো ক্র্যাশ-টেস্ট নেই। একটি শুরু করুন, বা ফিচারড ডেমো খুলুন।",
    open: "খুলুন",
    quick: "নিরীক্ষা ঘুরে দেখুন",
    featured: "ফিচারড ডেমো",
    featuredSub: "আসল পাবলিক SEC ফাইলিং, খুলতে প্রস্তুত",
    status: {
      queued: "অপেক্ষমাণ",
      running: "চলছে",
      done: "সম্পন্ন",
      failed: "ব্যর্থ",
      blocked: "আটকানো",
    } as Record<string, string>,
    actions: [
      {
        href: "/crash-test",
        title: "নতুন ক্র্যাশ-টেস্ট",
        desc: "কোম্পানির ফাইলিং দিয়ে সিদ্ধান্ত যাচাই",
      },
      {
        href: "/replay",
        title: "SVB রিপ্লে",
        desc: "মার্চ ২০২৩-এর আগের সতর্কসংকেত",
      },
      {
        href: "/graph",
        title: "সম্পর্কের গ্রাফ",
        desc: "ডিরেক্টর, কমিটি, ইন্টারলক",
      },
      {
        href: "/radar",
        title: "রেগুলেটরি রাডার",
        desc: "নিয়ম পরিবর্তনের অ্যালার্ট অনুমোদন/বাতিল",
      },
      { href: "/reports", title: "রিপোর্ট", desc: "সব রিপোর্ট ও লিগ্যাল মেমো" },
      {
        href: "/docs",
        title: "ডকস ও স্ট্যাটাস",
        desc: "আর্কিটেকচার, পদ্ধতি, লাইভ স্ট্যাটাস",
      },
    ],
    demos: [
      {
        name: "সিলিকন ভ্যালি ব্যাংক",
        note: "৭ মার্চ ২০২৩-এ ফ্রিজ · রিপ্লে কেস",
        score: 68,
      },
      { name: "অ্যাপল ইনক.", note: "সুস্থ কোম্পানির তুলনা", score: 85 },
      { name: "অ্যাপল ইনক. · প্রাইভেট", note: "সব AI লোকাল মডেলে", score: 94 },
    ],
  },
};

type Row = Record<string, unknown>;

function num(v: unknown): number | null {
  const n = typeof v === "number" ? v : typeof v === "string" ? Number(v) : NaN;
  return Number.isFinite(n) ? n : null;
}

function scoreOf(r: Row): number | null {
  const health = r.health as Row | undefined;
  return (
    num(r.health_score) ?? num(r.score) ?? (health ? num(health.score) : null)
  );
}

function scoreColor(s: number | null): string {
  if (s === null) return "#8b95a7";
  if (s >= 80) return "#2ea043";
  if (s >= 60) return "#f5b942";
  return "#e5534b";
}

function ScoreRing({
  score,
  size = 52,
}: {
  score: number | null;
  size?: number;
}) {
  const r = (size - 8) / 2;
  const c = 2 * Math.PI * r;
  const pct = score === null ? 0 : Math.max(0, Math.min(100, score)) / 100;
  const color = scoreColor(score);
  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      aria-hidden="true"
      className="shrink-0"
    >
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke="currentColor"
        strokeOpacity="0.15"
        strokeWidth="5"
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth="5"
        strokeLinecap="round"
        strokeDasharray={`${c * pct} ${c}`}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
      <text
        x="50%"
        y="50%"
        dominantBaseline="central"
        textAnchor="middle"
        fontSize={size * 0.3}
        fontWeight="700"
        fill={color}
      >
        {score === null ? "–" : Math.round(score)}
      </text>
    </svg>
  );
}

const ICONS: Record<string, string> = {
  "/crash-test": "M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7l8-4z M9 12l2 2 4-4",
  "/replay": "M3 12a9 9 0 1 0 3-6.7 M3 4v5h5 M12 8v4l3 2",
  "/graph":
    "M6 6m-2 0a2 2 0 1 0 4 0a2 2 0 1 0-4 0 M18 6m-2 0a2 2 0 1 0 4 0a2 2 0 1 0-4 0 M12 18m-2 0a2 2 0 1 0 4 0a2 2 0 1 0-4 0 M7.5 7.5l3.5 9 M16.5 7.5l-3.5 9 M8 6h8",
  "/radar":
    "M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0-18 0 M12 12m-5 0a5 5 0 1 0 10 0a5 5 0 1 0-10 0 M12 12l6-6",
  "/reports": "M7 3h7l5 5v13H7z M14 3v5h5 M10 13h6 M10 17h6",
  "/docs": "M4 5h7a3 3 0 0 1 3 3v12a2 2 0 0 0-2-2H4z M20 5h-5a3 3 0 0 0-3 3",
};

function Icon({ path }: { path: string }) {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={path} />
    </svg>
  );
}

export default function DashboardPage() {
  const { t } = useApp();
  const { user, usage, loading } = useSession();
  const router = useRouter();
  const lang: "en" | "bn" = t("dash.hello") === "Welcome" ? "en" : "bn";
  const s = L[lang];

  const [tests, setTests] = useState<Row[] | null>(null);
  const [radarPending, setRadarPending] = useState<number | null>(null);

  useEffect(() => {
    if (!loading && !user) router.replace("/login?next=/dashboard");
  }, [loading, user, router]);

  useEffect(() => {
    if (!user) return;
    getMyCrashTests()
      .then((rows) => setTests((rows as unknown as Row[]) ?? []))
      .catch(() => setTests([]));
    getRadar()
      .then((data) => {
        const alerts =
          ((data as unknown as Row).alerts as Row[] | undefined) ?? [];
        setRadarPending(
          alerts.filter(
            (a) => (a.status ?? a.decision ?? "pending") === "pending",
          ).length,
        );
      })
      .catch(() => setRadarPending(null));
  }, [user]);

  const stats = useMemo(() => {
    const rows = tests ?? [];
    const scores = rows.map(scoreOf).filter((x): x is number => x !== null);
    return {
      total: rows.length,
      done: rows.filter((r) => r.status === "done").length,
      avg: scores.length
        ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
        : null,
    };
  }, [tests]);

  if (loading || !user) {
    return (
      <main className="bg-app min-h-[calc(100vh-4rem)] px-4 py-16 text-center text-muted">
        {t("dash.loading")}
      </main>
    );
  }

  const used = usage?.used_this_month ?? 0;
  const limit = usage?.limit ?? null;
  const pct = limit ? Math.min(100, Math.round((used / limit) * 100)) : 0;
  const today = new Date().toLocaleDateString(
    lang === "bn" ? "bn-BD" : "en-US",
    { weekday: "long", day: "numeric", month: "long", year: "numeric" },
  );
  const recent = (tests ?? []).slice(0, 5);

  const statCards = [
    { label: s.runs, value: tests === null ? "…" : String(stats.total) },
    {
      label: s.avg,
      value:
        tests === null ? "…" : stats.avg === null ? "–" : String(stats.avg),
      color: scoreColor(stats.avg),
    },
    { label: s.done, value: tests === null ? "…" : String(stats.done) },
    {
      label: s.radar,
      value: radarPending === null ? "–" : String(radarPending),
      href: "/radar",
    },
  ];

  return (
    <main className="bg-app min-h-[calc(100vh-4rem)] overflow-x-hidden text-text">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
        {/* Hero */}
        <section className="relative overflow-hidden rounded-2xl border border-border bg-surface p-6 sm:p-8">
          <div className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-accent/10 blur-3xl" />
          <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-sm text-muted">{today}</p>
              <div className="mt-1 flex flex-wrap items-center gap-3">
                <h1 className="text-2xl font-bold sm:text-3xl">
                  {t("dash.hello")}, {user.name}
                </h1>
                {user.role === "demo" && (
                  <span className="rounded-full bg-accent/15 px-3 py-1 text-xs font-semibold text-accent">
                    {t("dash.demoBadge")}
                  </span>
                )}
                {user.role === "admin" && (
                  <span className="rounded-full bg-conf-medium/15 px-3 py-1 text-xs font-semibold text-conf-medium">
                    {t("dash.adminBadge")}
                  </span>
                )}
              </div>
              <p className="mt-2 text-muted">{s.sub}</p>
              <div className="mt-5 flex flex-wrap gap-3">
                <Link
                  href="/crash-test"
                  className="rounded-lg bg-accent px-5 py-3 font-semibold text-accent-contrast shadow-lg shadow-accent/20 hover:opacity-90"
                >
                  {t("dash.new")}
                </Link>
                <Link
                  href="/pricing"
                  className="rounded-lg border border-border px-5 py-3 font-semibold hover:bg-surface-2"
                >
                  {t("dash.upgrade")}
                </Link>
                {user.role === "admin" && (
                  <Link
                    href="/admin"
                    className="rounded-lg border border-conf-medium/60 px-5 py-3 font-semibold text-conf-medium hover:bg-conf-medium/10"
                  >
                    {t("dash.admin")}
                  </Link>
                )}
              </div>
            </div>
            <div className="grid min-w-[260px] gap-3 rounded-xl border border-border bg-surface-2/60 p-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-muted">
                  {t("dash.plan")}
                </p>
                <p className="text-lg font-semibold">
                  {user.role === "user"
                    ? PLAN_NAMES[user.plan]
                    : t("dash.demoBadge")}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-muted">
                  {t("dash.usage")}
                </p>
                <p className="text-lg font-semibold">
                  {usage?.unlimited
                    ? t("dash.unlimited")
                    : `${used} / ${limit}`}
                </p>
                {!usage?.unlimited && (
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-bg">
                    <div
                      className="h-full rounded-full bg-accent"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                )}
              </div>
            </div>
          </div>
        </section>

        {/* Stats */}
        <section className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {statCards.map((c) => {
            const body = (
              <>
                <p className="text-sm text-muted">{c.label}</p>
                <p
                  className="mt-2 text-3xl font-bold"
                  style={c.color ? { color: c.color } : undefined}
                >
                  {c.value}
                </p>
              </>
            );
            return c.href ? (
              <Link
                key={c.label}
                href={c.href}
                className="rounded-xl border border-border bg-surface p-5 transition hover:-translate-y-0.5 hover:border-accent/60"
              >
                {body}
              </Link>
            ) : (
              <div
                key={c.label}
                className="rounded-xl border border-border bg-surface p-5"
              >
                {body}
              </div>
            );
          })}
        </section>

        <div className="mt-6 grid gap-6 lg:grid-cols-5">
          {/* Recent */}
          <section className="min-w-0 rounded-xl border border-border bg-surface p-5 lg:col-span-3">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-semibold">{s.recent}</h2>
              <Link
                href="/reports"
                className="text-sm font-semibold text-accent hover:underline"
              >
                {s.viewAll} →
              </Link>
            </div>
            {tests === null ? (
              <div className="mt-4 space-y-3">
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="h-16 animate-pulse rounded-lg bg-surface-2"
                  />
                ))}
              </div>
            ) : recent.length === 0 ? (
              <div className="mt-6 rounded-lg border border-dashed border-border p-6 text-center text-muted">
                <p>{s.empty}</p>
                <Link
                  href="/crash-test"
                  className="mt-4 inline-block rounded-lg bg-accent px-4 py-2 font-semibold text-accent-contrast"
                >
                  {t("dash.new")}
                </Link>
              </div>
            ) : (
              <ul className="mt-4 divide-y divide-border">
                {recent.map((r) => {
                  const id = String(r.id ?? "");
                  const status = String(r.status ?? "done");
                  const company = String(r.company ?? r.cik ?? "");
                  return (
                    <li key={id} className="flex items-center gap-4 py-3">
                      <ScoreRing
                        score={status === "done" ? scoreOf(r) : null}
                      />
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-semibold">{company}</p>
                        <p className="truncate text-sm text-muted">
                          {String(r.decision ?? "")}
                        </p>
                        <p className="mt-0.5 text-xs text-muted">
                          {String(r.as_of ?? "")} · {s.status[status] ?? status}
                          {r.private ? " · 🔒" : ""}
                        </p>
                      </div>
                      <Link
                        href={
                          status === "done"
                            ? `/report/${id}`
                            : `/crash-test/${id}`
                        }
                        className="shrink-0 rounded-lg border border-border px-3 py-1.5 text-sm font-semibold hover:bg-surface-2"
                      >
                        {s.open}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          {/* Featured */}
          <section className="min-w-0 rounded-xl border border-border bg-surface p-5 lg:col-span-2">
            <h2 className="text-lg font-semibold">{s.featured}</h2>
            <p className="text-sm text-muted">{s.featuredSub}</p>
            <ul className="mt-4 space-y-3">
              {s.demos.map((d) => (
                <li key={d.name}>
                  <Link
                    href="/reports#featured"
                    className="flex items-center gap-4 rounded-lg border border-border p-3 transition hover:border-accent/60 hover:bg-surface-2"
                  >
                    <ScoreRing score={d.score} size={46} />
                    <div className="min-w-0">
                      <p className="truncate font-semibold">{d.name}</p>
                      <p className="truncate text-xs text-muted">{d.note}</p>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        </div>

        {/* Quick actions */}
        <section className="mt-6">
          <h2 className="text-lg font-semibold">{s.quick}</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {s.actions.map((a) => (
              <Link
                key={a.href}
                href={a.href}
                className="group flex items-start gap-4 rounded-xl border border-border bg-surface p-5 transition hover:-translate-y-0.5 hover:border-accent/60"
              >
                <span className="rounded-lg bg-accent/15 p-2.5 text-accent transition group-hover:bg-accent group-hover:text-accent-contrast">
                  <Icon path={ICONS[a.href]} />
                </span>
                <span>
                  <span className="block font-semibold">{a.title}</span>
                  <span className="mt-0.5 block text-sm text-muted">
                    {a.desc}
                  </span>
                </span>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
