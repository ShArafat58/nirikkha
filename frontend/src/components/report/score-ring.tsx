"use client";

import { useEffect, useState } from "react";

const BAND_COLOR: Record<string, string> = {
  low_concern: "var(--sev-low)", moderate_concern: "var(--sev-medium)",
  elevated_concern: "var(--sev-high)", high_concern: "var(--sev-critical)",
};

export function ScoreRing({ score, band, size = 196 }: { score: number; band: string; size?: number }) {
  const [shown, setShown] = useState(0);
  useEffect(() => {
    const timer = setTimeout(() => setShown(score), 80);
    return () => clearTimeout(timer);
  }, [score]);
  const r = 80;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, shown)) / 100;
  const color = BAND_COLOR[band] ?? "var(--accent)";
  return (
    <svg viewBox="0 0 200 200" width={size} height={size} role="img" aria-label={`Governance Health Score ${score} out of 100`}>
      <circle cx="100" cy="100" r={r} fill="none" stroke="var(--surface-2)" strokeWidth="14" />
      <circle cx="100" cy="100" r={r} fill="none" stroke={color} strokeWidth="14" strokeLinecap="round"
              strokeDasharray={c} strokeDashoffset={c * (1 - pct)} transform="rotate(-90 100 100)"
              style={{ transition: "stroke-dashoffset 1.2s cubic-bezier(.2,.8,.2,1)", filter: `drop-shadow(0 0 10px ${color})` }} />
      <text x="100" y="104" textAnchor="middle" fontSize="56" fontWeight="700" fill="var(--text)"
            style={{ fontFamily: "var(--font-plex-mono)" }}>{score}</text>
      <text x="100" y="132" textAnchor="middle" fontSize="14" fill="var(--muted)" style={{ fontFamily: "var(--font-plex-mono)" }}>/ 100</text>
    </svg>
  );
}