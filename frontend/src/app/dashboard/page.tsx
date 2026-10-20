"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useApp } from "../../components/providers";
import { useSession } from "../../components/session";

const PLAN_NAMES: Record<string, string> = { free: "Free", analyst_pro: "Analyst Pro", team: "Team", enterprise: "Enterprise" };

export default function DashboardPage() {
  const { t } = useApp();
  const { user, usage, loading } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login?next=/dashboard");
  }, [loading, user, router]);

  if (loading || !user) {
    return <main className="bg-app min-h-[calc(100vh-4rem)] px-4 py-16 text-center text-muted">{t("dash.loading")}</main>;
  }

  const used = usage?.used_this_month ?? 0;
  const limit = usage?.limit ?? null;
  const pct = limit ? Math.min(100, Math.round((used / limit) * 100)) : 0;

  return (
    <main className="bg-app min-h-[calc(100vh-4rem)] text-text">
      <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold text-text sm:text-3xl">{t("dash.hello")}, {user.name}</h1>
          {user.role === "demo" && <span className="rounded-full bg-accent/15 px-3 py-1 text-xs font-semibold text-accent">{t("dash.demoBadge")}</span>}
          {user.role === "admin" && <span className="rounded-full bg-conf-medium/15 px-3 py-1 text-xs font-semibold text-conf-medium">{t("dash.adminBadge")}</span>}
        </div>

        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          <section className="rounded-xl border border-border bg-surface p-5">
            <p className="text-sm text-muted">{t("dash.plan")}</p>
            <p className="mt-1 text-xl font-semibold text-text">{user.role === "user" ? PLAN_NAMES[user.plan] : t("dash.demoBadge")}</p>
          </section>
          <section className="rounded-xl border border-border bg-surface p-5">
            <p className="text-sm text-muted">{t("dash.usage")}</p>
            <p className="mt-1 text-xl font-semibold text-text">{usage?.unlimited ? t("dash.unlimited") : `${used} / ${limit}`}</p>
            {!usage?.unlimited && (
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-surface-2">
                <div className="h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
              </div>
            )}
          </section>
        </div>

        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/crash-test" className="rounded-lg bg-accent px-5 py-3 font-semibold text-accent-contrast hover:opacity-90">{t("dash.new")}</Link>
          <Link href="/pricing" className="rounded-lg border border-border px-5 py-3 font-semibold text-text hover:bg-surface-2">{t("dash.upgrade")}</Link>
          {user.role === "admin" && (
            <Link href="/admin" className="rounded-lg border border-conf-medium/60 px-5 py-3 font-semibold text-conf-medium hover:bg-conf-medium/10">{t("dash.admin")}</Link>
          )}
        </div>
      </div>
    </main>
  );
}