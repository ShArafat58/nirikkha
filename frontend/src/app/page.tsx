"use client";

import Link from "next/link";

import { useApp } from "../components/providers";
import { useSession } from "../components/session";
import { LandingSections } from "../components/landing-sections";

export default function Home() {
  const { t } = useApp();
  const { signedIn: user } = useSession();
  return (
    <main data-theme="dark" className="bg-bg text-text">
      <div className="bg-landing relative overflow-hidden">
      <section className="relative z-10 mx-auto flex min-h-[calc(100vh-4rem)] max-w-7xl items-center px-5 py-12 sm:px-6 sm:py-16">
        <div className="w-full max-w-xl">
          <h1 className="hero-shadow text-[2.6rem] font-bold leading-[1.15] sm:text-6xl sm:leading-tight">{t("hero.title")}</h1>
          <p className="hero-shadow mt-6 max-w-lg text-xl text-text/85 sm:text-2xl">{t("hero.subtitle")}</p>

          <div className="mt-10 flex flex-col gap-3 sm:mt-8 sm:flex-row sm:flex-wrap">
            <Link href="/crash-test"
                  className="rounded-lg bg-accent px-5 py-3.5 text-center font-semibold text-accent-contrast shadow-lg shadow-accent/20 hover:opacity-90">
              {t("hero.cta")}
            </Link>
            <Link href={user ? "/dashboard" : "/login?demo=1&next=/crash-test"}
                  className="rounded-lg border border-accent/60 bg-bg/40 px-5 py-3.5 text-center font-semibold text-accent backdrop-blur hover:bg-accent/10">
              {user ? t("hero.goDashboard") : t("hero.demo")}
            </Link>
            <Link href="/pricing" className="rounded-lg px-5 py-3 text-center font-semibold text-text underline decoration-accent/70 underline-offset-4 hover:text-accent">
              {t("hero.plans")} →
            </Link>
          </div>

          <ul className="hero-shadow mt-10 flex flex-col gap-2.5 text-sm text-text/85 sm:flex-row sm:flex-wrap sm:gap-x-6 sm:gap-y-2">
            {(["hero.point1", "hero.point2", "hero.point3"] as const).map((key) => (
              <li key={key} className="flex items-center gap-2">
                <span className="mt-0.5 text-accent" aria-hidden>✓</span>
                {t(key)}
              </li>
            ))}
          </ul>
        </div>
      </section>
        <div aria-hidden className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-b from-transparent to-bg" />
      </div>
      <LandingSections />
    </main>
  );
}