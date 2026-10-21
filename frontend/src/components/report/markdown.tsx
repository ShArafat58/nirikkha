// Safe Markdown renderer for legal memos (no raw HTML). Styled as a printable light document.
import type { ReactNode } from "react";

const SEVERITY: Record<string, string> = {
  high: "bg-rose-100 text-rose-700 border-rose-300",
  medium: "bg-amber-100 text-amber-800 border-amber-300",
  low: "bg-slate-100 text-slate-700 border-slate-300",
  "উচ্চ": "bg-rose-100 text-rose-700 border-rose-300",
  "মাঝারি": "bg-amber-100 text-amber-800 border-amber-300",
  "নিম্ন": "bg-slate-100 text-slate-700 border-slate-300",
};

function inline(text: string, key: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|`[^`]+`|\[[^\]]+\]\(https?:\/\/[^)\s]+\)|\(?https?:\/\/[^\s)]+\)?)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const tok = m[0];
    const k = `${key}-${i++}`;
    if (tok.startsWith("**")) out.push(<strong key={k} className="font-semibold text-slate-900">{tok.slice(2, -2)}</strong>);
    else if (tok.startsWith("`")) out.push(<code key={k} className="rounded bg-slate-100 px-1 font-mono text-[0.9em]">{tok.slice(1, -1)}</code>);
    else if (tok.startsWith("[")) {
      const [, label, url] = tok.match(/^\[([^\]]+)\]\((.+)\)$/) ?? [];
      out.push(<a key={k} href={url} target="_blank" rel="noreferrer" className="text-sky-700 underline">{label}</a>);
    } else if (/https?:\/\//.test(tok)) {
      const url = tok.replace(/^\(|\)$/g, "");
      out.push(<a key={k} href={url} target="_blank" rel="noreferrer" className="whitespace-nowrap text-sky-700 underline">SEC filing ↗</a>);
    } else out.push(<em key={k}>{tok.slice(1, -1)}</em>);
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

function RiskHeading({ text, k }: { text: string; k: string }) {
  const m = text.match(/^(\d+)[.)]\s+(.*?)\s*\((high|medium|low|উচ্চ|মাঝারি|নিম্ন)\)\s*[-–—]?\s*(.*)$/i);
  if (!m) return <h3 className="mt-6 text-lg font-semibold text-slate-900">{inline(text, k)}</h3>;
  const [, n, title, sev, rest] = m;
  return (
    <div className="mt-8 break-inside-avoid rounded-xl border border-slate-200 bg-slate-50 p-4" style={{ printColorAdjust: "exact", WebkitPrintColorAdjust: "exact" }}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-900 text-sm font-bold text-white">{n}</span>
        <span className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold uppercase ${SEVERITY[sev.toLowerCase()] ?? SEVERITY.low}`}>{sev}</span>
        {rest && <span className="rounded-full border border-sky-300 bg-sky-50 px-2.5 py-0.5 text-xs text-sky-700">{rest}</span>}
      </div>
      <h3 className="mt-2 text-lg font-semibold leading-snug text-slate-900">{inline(title, k)}</h3>
    </div>
  );
}

export function Markdown({ text }: { text: string }) {
  const blocks: ReactNode[] = [];
  let list: string[] = [];
  let ordered = false;
  const flush = () => {
    if (!list.length) return;
    const items = list.map((l, i) => <li key={i}>{inline(l, `li${blocks.length}-${i}`)}</li>);
    blocks.push(ordered
      ? <ol key={blocks.length} className="ml-6 list-decimal space-y-1.5">{items}</ol>
      : <ul key={blocks.length} className="ml-6 list-disc space-y-1.5">{items}</ul>);
    list = [];
  };
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trimEnd();
    const li = line.match(/^\s*[-*]\s+(.*)$/);
    const ol = line.match(/^\s*\d+[.)]\s+(.*)$/);
    if ((li && !line.trim().startsWith("*")) || (li && /^\s*-/.test(line)) || ol) {
      if (list.length && ordered !== Boolean(ol)) flush();
      ordered = Boolean(ol);
      list.push((li ?? ol)![1]);
      continue;
    }
    flush();
    const k = `b${blocks.length}`;
    if (!line.trim()) continue;
    const label = line.match(/^\*([^*]+):\*\s*(.*)$/);
    if (line.startsWith("### ")) blocks.push(<RiskHeading key={k} k={k} text={line.slice(4)} />);
    else if (line.startsWith("## ")) blocks.push(<h2 key={k} className="mt-10 border-b-2 border-slate-900 pb-1.5 text-xl font-bold text-slate-900">{inline(line.slice(3), k)}</h2>);
    else if (line.startsWith("# ")) blocks.push(<h1 key={k} className="text-3xl font-bold text-slate-900">{inline(line.slice(2), k)}</h1>);
    else if (line.startsWith("> ")) blocks.push(<blockquote key={k} className="border-l-4 border-amber-400 bg-amber-50 py-2 pl-4 italic">{inline(line.slice(2), k)}</blockquote>);
    else if (/^-{3,}$/.test(line)) blocks.push(<hr key={k} className="border-slate-200" />);
    else if (label) blocks.push(
      <p key={k} className="leading-relaxed">
        <span className="mr-2 text-[11px] font-bold uppercase tracking-wider text-slate-500">{label[1]}</span>{inline(label[2], k)}
      </p>);
    else if (/^\[[A-Z]+-\d+\]/.test(line)) blocks.push(
      <p key={k} className="break-inside-avoid border-l-2 border-slate-300 pl-3 text-sm text-slate-600">{inline(line, k)}</p>);
    else blocks.push(<p key={k} className="leading-relaxed">{inline(line, k)}</p>);
  }
  flush();
  return <div className="space-y-3 text-[15px] text-slate-700">{blocks}</div>;
}