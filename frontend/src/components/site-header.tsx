"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getStatus, type Status } from "../lib/api";
import { useApp } from "./providers";
import { useSession } from "./session";

type ServerState = "checking" | "live" | "demo" | "offline";

const NAV = [
  { href: "/crash-test", key: "nav.crashTest" }, { href: "/reports", key: "nav.reports" },
  { href: "/replay", key: "nav.replay" }, { href: "/graph", key: "nav.graph" },
  { href: "/radar", key: "nav.radar" },
  { href: "/pricing", key: "nav.pricing" },
  { href: "/docs", key: "nav.docs" },
] as const;

function stateOf(status: Status): ServerState {
  return status.worker_online ? "live" : "demo";
}

export function SiteHeader() {
  const { t, theme, setTheme, lang, setLang } = useApp();
  const [server, setServer] = useState<ServerState>("checking");
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const { signedIn, signOut } = useSession();
  const router = useRouter();
  const logout = () => {
    signOut();
    router.push("/");
  };

  useEffect(() => {
    let alive = true;
    const check = () =>
      getStatus()
        .then((s) => alive && setServer(stateOf(s)))
        .catch(() => alive && setServer("offline"));
    check();
    const timer = setInterval(check, 60_000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, []);

  useEffect(() => setOpen(false), [pathname]);

  const dot = { checking: "bg-muted animate-pulse", live: "bg-conf-high", demo: "bg-accent", offline: "bg-sev-critical" }[server];
  const label = { checking: t("status.checking"), live: t("status.live"), demo: t("status.demo"), offline: t("status.offline") }[server];
  const themeLabel = theme === "dark" ? `☀ ${t("theme.paper")}` : `☾ ${t("theme.dark")}`;
  const toggleTheme = () => setTheme(theme === "dark" ? "paper" : "dark");
  const toggleLang = () => setLang(lang === "en" ? "bn" : "en");
  const ghost = "rounded-md border border-border px-3 py-1.5 text-sm text-muted hover:text-text";

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-bg/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-3 px-4 sm:px-6">
        <Link href={signedIn ? "/dashboard" : "/"} className="flex shrink-0 items-center gap-2.5" aria-label="Nirikkha home">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/brand/icon.svg" alt="" className="h-9 w-9 sm:h-10 sm:w-10" />
          <span className="flex flex-col leading-none">
            <span className="text-lg font-bold tracking-tight text-text sm:text-xl">Nirikkha</span>
            <span lang="bn" className="mt-1 text-[12px] font-medium text-accent sm:text-[13px]" style={{ fontFamily: "var(--font-noto-bn)" }}>
              নিরীক্ষা
            </span>
          </span>
        </Link>

        <nav className="hidden items-center gap-1 lg:flex" aria-label="Main">
          {NAV.map((item) => (
            <Link key={item.href} href={item.href}
                  className={`rounded-md px-3 py-2 text-sm transition hover:bg-surface-2 hover:text-text ${pathname.startsWith(item.href) ? "text-text" : "text-muted"}`}>
              {t(item.key)}
            </Link>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <span className="hidden items-center gap-2 rounded-full border border-border px-3 py-1 text-xs text-muted xl:inline-flex" title={label}>
            <span className={`h-2 w-2 rounded-full ${dot}`} aria-hidden />
            {label}
          </span>
          <button type="button" onClick={toggleTheme} className={`hidden sm:inline-flex ${ghost}`} aria-label={t("theme.toggle")}>
            {themeLabel}
          </button>
          <button type="button" onClick={toggleLang} className={`hidden sm:inline-flex ${ghost}`}>
            {t("lang.toggle")}
          </button>
          {(
            <Link href="/admin" className={`hidden sm:inline-flex ${ghost} border-conf-medium/60 text-conf-medium`}>{t("nav.admin")}</Link>
          )}
          {signedIn ? (
            <>
              <Link href="/dashboard"
                    className="whitespace-nowrap rounded-md bg-accent px-3 py-1.5 text-sm font-semibold text-accent-contrast hover:opacity-90">
                {t("nav.dashboard")}
              </Link>
              <button type="button" onClick={logout} className={`hidden sm:inline-flex ${ghost}`}>{t("nav.logout")}</button>
            </>
          ) : (
            <Link href="/login"
                  className="whitespace-nowrap rounded-md bg-accent px-3 py-1.5 text-sm font-semibold text-accent-contrast hover:opacity-90">
              {t("nav.login")}
            </Link>
          )}
          <button type="button" onClick={() => setOpen((v) => !v)}
                  className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border text-text lg:hidden"
                  aria-label="Menu" aria-expanded={open} aria-controls="mobile-menu">
            <span aria-hidden className="text-lg leading-none">{open ? "✕" : "☰"}</span>
          </button>
        </div>
      </div>

      {open && (
        <div id="mobile-menu" className="border-t border-border bg-bg px-4 pb-4 pt-2 lg:hidden">
          <nav className="flex flex-col" aria-label="Mobile">
            {NAV.map((item) => (
              <Link key={item.href} href={item.href} className="rounded-md px-2 py-3 text-base text-text hover:bg-surface-2">
                {t(item.key)}
              </Link>
            ))}
          </nav>
          <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-border pt-3">
            <button type="button" onClick={toggleTheme} className={ghost}>{themeLabel}</button>
            <button type="button" onClick={toggleLang} className={ghost}>{t("lang.toggle")}</button>
            {signedIn && <button type="button" onClick={logout} className={ghost}>{t("nav.logout")}</button>}
            {<Link href="/admin" className={ghost}>{t("nav.admin")}</Link>}
            <span className="inline-flex items-center gap-2 text-xs text-muted">
              <span className={`h-2 w-2 rounded-full ${dot}`} aria-hidden />
              {label}
            </span>
          </div>
        </div>
      )}
    </header>
  );
}