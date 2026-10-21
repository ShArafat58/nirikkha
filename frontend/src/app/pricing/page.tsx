"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useApp } from "../../components/providers";
import { useSession } from "../../components/session";
import { Alert, Button } from "../../components/ui";
import { ApiError, cancelPlan, getPlans, requestPlan, type PlansResponse, type Plan } from "../../lib/api";

import PricingFaqI18n from "../../components/pricing-faq-i18n";
export default function PricingPage() {
  const { t } = useApp();
  const { user, signedIn, refresh } = useSession();
  const router = useRouter();
  const [data, setData] = useState<PlansResponse | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  useEffect(() => {
    getPlans().then(setData).catch((err) => setError(err instanceof ApiError ? err.message : t("auth.err.generic")));
  }, [t]);

  const current = signedIn && user?.role === "user" ? user.plan : null;

  async function pilot() {
    if (!signedIn) return router.push("/login?next=/pricing");
    setBusy("enterprise");
    setError("");
    try {
      await requestPlan("enterprise", "pilot", "Requested from the pricing page");
      setMessage(t("price.pilotSent"));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("auth.err.generic"));
    } finally {
      setBusy("");
    }
  }

  async function toFree() {
    setBusy("free");
    setError("");
    try {
      await cancelPlan();
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("auth.err.generic"));
    } finally {
      setBusy("");
    }
  }

  function action(p: Plan) {
    const isCurrent = current === p.id;
    const base = "w-full";
    if (isCurrent) return <Button variant="ghost" className={base} disabled>{t("price.current")}</Button>;
    if (p.id === "free") {
      if (!signedIn) return <Link href="/signup" className="block rounded-lg border border-border px-4 py-2.5 text-center text-sm font-semibold hover:bg-surface-2">{t("price.startFree")}</Link>;
      if (user?.role !== "user") return null;
      return <Button variant="ghost" className={base} loading={busy === "free"} onClick={toFree}>{t("price.switchFree")}</Button>;
    }
    if (p.price_usd === null) return <Button variant="secondary" className={base} loading={busy === "enterprise"} onClick={pilot}>{t("price.pilot")}</Button>;
    const href = `/checkout?plan=${p.id}`;
    return (
      <Link href={signedIn ? href : `/login?next=${encodeURIComponent(href)}`}
            className="block rounded-lg bg-accent px-4 py-2.5 text-center text-sm font-semibold text-accent-contrast hover:opacity-90">
        {t("price.subscribe")}
      </Link>
    );
  }

  return (
    <main className="relative min-h-[calc(100vh-4rem)] overflow-hidden bg-bg text-text">
      <div aria-hidden className="pointer-events-none fixed inset-0 bg-[url('/images/bg/pricing.webp')] bg-cover bg-center opacity-[0.13]" />
      <section className="relative">
        <div className="mx-auto max-w-7xl px-4 pb-4 pt-16 text-center sm:px-6 sm:pt-20">
          <div className="mx-auto max-w-2xl">
            <h1 className="text-4xl font-bold leading-tight sm:text-5xl">{t("price.title")}</h1>
            <p className="mt-4 text-lg text-text/85">{t("price.subtitle")}</p>
            <p className="mt-3 text-sm text-muted">{t("price.note")}</p>
          </div>
        </div>
      </section>

      <div className="relative mx-auto max-w-7xl px-4 py-12 sm:px-6">
        {user?.role === "demo" && <div className="mb-6"><Alert kind="info">{t("price.demoUser")}</Alert></div>}
        {message && <div className="mb-6"><Alert kind="success">{message}</Alert></div>}
        {error && <div className="mb-6"><Alert>{error}</Alert></div>}

        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
          {(data?.plans ?? []).map((p) => {
            const featured = p.id === "analyst_pro";
            return (
              <article key={p.id}
                       className={`relative flex flex-col rounded-2xl border bg-surface/85 p-6 shadow-lg shadow-black/20 backdrop-blur ${featured ? "border-accent/70 ring-1 ring-accent/30" : "border-border"} ${current === p.id ? "outline outline-2 outline-conf-high/60" : ""}`}>
                {featured && <span className="absolute -top-3 left-6 rounded-full bg-accent px-3 py-0.5 text-xs font-semibold text-accent-contrast">{t("price.forAnalysts")}</span>}
                <h2 className="text-xl font-semibold">{p.name}</h2>
                <p className="mt-1 min-h-[2.5rem] text-sm text-muted">{p.audience}</p>
                <p className="mt-5">
                  {p.price_usd === null
                    ? <span className="text-2xl font-bold">{p.price_label}</span>
                    : <><span className="text-4xl font-bold">${p.price_usd}</span><span className="ml-1 text-sm text-muted">/ {p.price_unit}</span></>}
                </p>
                <p className="mt-2 text-sm font-medium text-accent">
                  {p.crash_tests_per_month === null ? t("price.unlimited") : `${p.crash_tests_per_month} ${t("price.perMonth")}`}
                </p>
                <ul className="mt-5 flex-1 space-y-2 text-sm">
                  {p.features.map((f) => <li key={f} className="flex gap-2"><span className="text-conf-high" aria-hidden>✓</span>{f}</li>)}
                </ul>
                <div className="mt-6">{action(p)}</div>
              </article>
            );
          })}
        </div>

        {data?.add_ons?.length ? (
          <section className="mt-12">
            <h2 className="text-xl font-semibold">{t("price.addons")}</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              {data.add_ons.map((a) => (
                <div key={a.id} className="flex items-start justify-between gap-4 rounded-2xl border border-border bg-surface/85 p-5 backdrop-blur">
                  <div><p className="font-semibold">{a.name}</p><p className="mt-1 text-sm text-muted">{a.description}</p></div>
                  <p className="whitespace-nowrap text-2xl font-bold">${a.price_usd}</p>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        <section className="mt-12 rounded-2xl border border-border bg-surface/85 p-6 backdrop-blur">
          <h2 className="text-lg font-semibold">{t("price.howTitle")}</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            {([["📱", "pay.mobile", "pay.mobileSub"], ["💳", "pay.card", "pay.cardSub"], ["🏦", "pay.bank", "pay.bankSub"]] as const).map(([icon, title, sub]) => (
              <div key={title} className="flex items-center gap-3 rounded-xl bg-surface-2 p-4">
                <span className="text-2xl" aria-hidden>{icon}</span>
                <span><span className="block font-medium">{t(title)}</span><span className="text-xs text-muted">{t(sub)}</span></span>
              </div>
            ))}
          </div>
          <p className="mt-4 text-sm leading-relaxed text-muted">{t("price.howBody")}</p>
        </section>
      </div>
    <PricingFaqI18n />
      </main>
  );
}