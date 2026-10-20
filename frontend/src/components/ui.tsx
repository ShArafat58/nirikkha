"use client";

import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";

import type { Key } from "../lib/i18n";
import { PASSWORD_RULES } from "../lib/validation";
import { useApp } from "./providers";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-accent text-accent-contrast hover:opacity-90",
  secondary: "border border-accent/60 text-accent hover:bg-accent/10",
  ghost: "border border-border text-text hover:bg-surface-2",
  danger: "bg-sev-critical text-white hover:opacity-90",
};

export function Button({ variant = "primary", loading = false, className = "", children, disabled, type = "button", ...rest }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; loading?: boolean }) {
  return (
    <button type={type} {...rest} disabled={disabled || loading}
            className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-60 ${VARIANTS[variant]} ${className}`}>
      {loading && <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden />}
      {children}
    </button>
  );
}

export function Field({ label, htmlFor, hint, error, action, children }:
  { label: string; htmlFor: string; hint?: string; error?: string; action?: ReactNode; children: ReactNode }) {
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <label htmlFor={htmlFor} className="text-sm font-medium text-text">{label}</label>
        {action}
      </div>
      {children}
      {error ? <p className="mt-1.5 text-xs text-sev-critical" role="alert">{error}</p>
             : hint ? <p className="mt-1.5 text-xs text-muted">{hint}</p> : null}
    </div>
  );
}

const control = "w-full rounded-lg border bg-surface-2 px-3 py-2.5 text-sm text-text placeholder:text-muted/70 focus:border-accent focus:outline-none";

export function Input({ invalid = false, className = "", ...rest }: InputHTMLAttributes<HTMLInputElement> & { invalid?: boolean }) {
  return <input {...rest} aria-invalid={invalid || undefined}
                className={`${control} ${invalid ? "border-sev-critical" : "border-border"} ${className}`} />;
}

export function Select({ invalid = false, className = "", children, ...rest }:
  SelectHTMLAttributes<HTMLSelectElement> & { invalid?: boolean }) {
  return (
    <select {...rest} aria-invalid={invalid || undefined}
            className={`${control} ${invalid ? "border-sev-critical" : "border-border"} ${className}`}>
      {children}
    </select>
  );
}

export function Alert({ kind = "error", children }: { kind?: "error" | "info" | "success"; children: ReactNode }) {
  const styles = {
    error: "border-sev-critical/50 bg-sev-critical/10 text-text",
    info: "border-conf-medium/50 bg-conf-medium/10 text-text",
    success: "border-conf-high/50 bg-conf-high/10 text-text",
  }[kind];
  return <div role={kind === "error" ? "alert" : "status"} className={`rounded-lg border px-3 py-2.5 text-sm ${styles}`}>{children}</div>;
}

export function PasswordChecklist({ password }: { password: string }) {
  const { t } = useApp();
  return (
    <ul className="mt-2 grid grid-cols-1 gap-1 text-xs sm:grid-cols-2" aria-label="Password rules">
      {PASSWORD_RULES.map((rule) => {
        const ok = rule.test(password);
        return (
          <li key={rule.key} className={`flex items-center gap-1.5 ${ok ? "text-conf-high" : "text-muted"}`}>
            <span aria-hidden>{ok ? "✓" : "○"}</span>
            {t(`auth.rule.${rule.key}` as Key)}
          </li>
        );
      })}
    </ul>
  );
}