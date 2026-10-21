"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { useApp } from "../providers";

export function MemoLink() {
  const app = useApp();
  const bn = (app as unknown as { lang?: string }).lang === "bn";
  const { id } = useParams<{ id: string }>();
  if (!id) return null;
  return (
    <Link href={`/report/${id}/memo`}
          className="inline-flex items-center gap-2 rounded-lg border border-amber-500/50 bg-amber-500/10 px-3 py-1.5 text-sm font-medium text-amber-500 hover:bg-amber-500/20">
      ⚖ {bn ? "লিগ্যাল মেমো" : "Legal memo"} →
    </Link>
  );
}