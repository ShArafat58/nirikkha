"use client";

import type { Key } from "../lib/i18n";
import { useApp } from "./providers";

const BAND_STYLE: Record<string, string> = {
  low_concern: "bg-sev-low/15 text-sev-low border-sev-low/40",
  moderate_concern: "bg-sev-medium/15 text-sev-medium border-sev-medium/40",
  elevated_concern: "bg-sev-high/15 text-sev-high border-sev-high/40",
  high_concern: "bg-sev-critical/15 text-sev-critical border-sev-critical/40",
};

export function BandBadge({ band }: { band: string | null | undefined }) {
  const { t } = useApp();
  if (!band) return null;
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${BAND_STYLE[band] ?? "border-border text-muted"}`}>
      {t(`band.${band}` as Key)}
    </span>
  );
}

export function ScoreNumber({ score, className = "" }: { score: number | null | undefined; className?: string }) {
  return <span className={`font-mono font-semibold tabular-nums ${className}`}>{score ?? "-"}<span className="text-muted">/100</span></span>;
}