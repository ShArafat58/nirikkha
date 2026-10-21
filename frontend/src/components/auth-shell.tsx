"use client";

import type { ReactNode } from "react";

import { useApp } from "./providers";

export function AuthShell({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  const { t } = useApp();
  return (
    <main className="min-h-[calc(100vh-4rem)] lg:grid lg:grid-cols-2">
      <aside data-theme="dark" className="bg-auth relative hidden overflow-hidden lg:block" aria-hidden>
        <div className="absolute inset-0 bg-gradient-to-r from-[#0b1220]/90 via-[#0b1220]/55 to-[#0b1220]/10" />
        <div className="relative flex h-full flex-col justify-center px-12 xl:px-16">
          <span className="h-1 w-14 rounded-full bg-accent" />
          <p className="mt-6 max-w-md text-5xl font-bold leading-tight text-text [text-shadow:0_2px_20px_rgba(11,18,32,0.8)]">
            {t("brand.tagline")}
          </p>
          <p className="mt-5 max-w-sm text-lg leading-relaxed text-text/80 [text-shadow:0_1px_10px_rgba(11,18,32,0.8)]">
            {t("auth.panel")}
          </p>
        </div>
      </aside>
      <div data-theme="dark" className="bg-auth h-36 lg:hidden" aria-hidden />
      <section className="bg-app flex justify-center px-4 py-10 text-text sm:px-6 lg:items-center">
        <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-xl sm:p-8">
          <h1 className="text-2xl font-bold text-text">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
          <div className="mt-6">{children}</div>
        </div>
      </section>
    </main>
  );
}