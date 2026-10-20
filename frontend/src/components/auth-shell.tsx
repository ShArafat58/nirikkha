"use client";

import type { ReactNode } from "react";

import { useApp } from "./providers";

export function AuthShell({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  const { t } = useApp();
  return (
    <main className="min-h-[calc(100vh-4rem)] lg:grid lg:grid-cols-2">
      <aside data-theme="dark" className="bg-auth relative hidden lg:block" aria-hidden>
        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-[#0b1220] via-[#0b1220]/80 to-transparent p-10 pt-24">
          <p className="text-3xl font-bold text-text">{t("brand.tagline")}</p>
          <p className="mt-2 max-w-md text-muted">{t("auth.panel")}</p>
        </div>
      </aside>
      <div data-theme="dark" className="bg-auth h-36 lg:hidden" aria-hidden />
      <section className="bg-app flex justify-center text-text px-4 py-10 sm:px-6 lg:items-center">
        <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-xl sm:p-8">
          <h1 className="text-2xl font-bold text-text">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
          <div className="mt-6">{children}</div>
        </div>
      </section>
    </main>
  );
}