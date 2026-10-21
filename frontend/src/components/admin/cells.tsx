// Small helpers shared by the admin tabs.
export type Row = Record<string, unknown>;

export function pick(row: Row, keys: string[]): unknown {
  for (const k of keys) {
    const v = k.split(".").reduce<unknown>((o, part) => (o && typeof o === "object" ? (o as Row)[part] : undefined), row);
    if (v !== undefined && v !== null && v !== "") return v;
  }
  return undefined;
}

export function str(v: unknown): string {
  return v === undefined || v === null ? "" : String(v);
}

export function when(v: unknown): string {
  if (!v) return "—";
  const d = new Date(String(v));
  return Number.isNaN(d.getTime()) ? String(v) : d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

const TONE: Record<string, string> = {
  done: "border-emerald-500/50 text-emerald-500", approved: "border-emerald-500/50 text-emerald-500",
  confirmed: "border-emerald-500/50 text-emerald-500", closed: "border-emerald-500/50 text-emerald-500",
  running: "border-sky-500/50 text-sky-500", queued: "border-slate-500/50 text-slate-400", open: "border-amber-500/50 text-amber-500",
  failed: "border-rose-500/50 text-rose-500", blocked: "border-rose-500/50 text-rose-500", rejected: "border-rose-500/50 text-rose-500",
  high: "border-rose-500/50 text-rose-500", medium: "border-amber-500/50 text-amber-500", low: "border-slate-500/50 text-slate-400",
};

export function Chip({ value }: { value: unknown }) {
  const v = str(value);
  if (!v) return null;
  return <span className={`inline-block rounded-full border px-2 py-0.5 text-[11px] font-semibold ${TONE[v.toLowerCase()] ?? "border-slate-500/40 opacity-80"}`}>{v}</span>;
}
export function Spinner() {
  return <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent align-[-2px]" aria-hidden />;
}
