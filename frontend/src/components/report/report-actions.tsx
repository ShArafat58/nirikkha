"use client";

// Spec Kit feature 001-report-share-export (specs/001-report-share-export/): copy share link and download JSON.
import { useParams } from "next/navigation";
import { useState } from "react";

import { useApp } from "../providers";
import { getCrashTest } from "../../lib/api";

const TXT = {
  en: {
    copy: "Copy share link",
    copied: "Link copied",
    copyFail: "Could not copy. Copy the address bar instead.",
    download: "Download JSON",
    downloading: "Preparing…",
    downloadFail: "Could not download the report. Please try again.",
    note: "Featured reports are public. Other reports ask the viewer to sign in.",
  },
  bn: {
    copy: "শেয়ার লিংক কপি করুন",
    copied: "লিংক কপি হয়েছে",
    copyFail: "কপি করা যায়নি। ব্রাউজারের ঠিকানা থেকে কপি করুন।",
    download: "JSON ডাউনলোড",
    downloading: "তৈরি হচ্ছে…",
    downloadFail: "রিপোর্ট ডাউনলোড করা যায়নি। আবার চেষ্টা করুন।",
    note: "ফিচার্ড রিপোর্ট সবার জন্য খোলা। অন্য রিপোর্ট দেখতে লগ ইন করতে হয়।",
  },
} as const;

const BTN =
  "inline-flex items-center gap-2 rounded-lg border border-amber-500/50 bg-amber-500/10 px-3 py-1.5 text-sm font-medium text-amber-500 hover:bg-amber-500/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 disabled:opacity-60";

async function copyText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    /* fall back below */
  }
  try {
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(area);
    return ok;
  } catch {
    return false;
  }
}

export function ReportActions() {
  const { lang } = useApp();
  const tx = TXT[lang === "bn" ? "bn" : "en"];
  const { id } = useParams<{ id: string }>();
  const [status, setStatus] = useState<string>("");
  const [busy, setBusy] = useState(false);

  if (!id) return null;

  const flash = (message: string) => {
    setStatus(message);
    window.setTimeout(() => setStatus(""), 2500);
  };

  const onCopy = async () => {
    const ok = await copyText(`${window.location.origin}/report/${id}`);
    flash(ok ? tx.copied : tx.copyFail);
  };

  const onDownload = async () => {
    setBusy(true);
    try {
      const data = await getCrashTest(id);
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `nirikkha-report-${id}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      flash(tx.downloadFail);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      <button type="button" onClick={onCopy} className={BTN}>
        🔗 {tx.copy}
      </button>
      <button
        type="button"
        onClick={onDownload}
        disabled={busy}
        className={BTN}
      >
        ⬇ {busy ? tx.downloading : tx.download}
      </button>
      <span aria-live="polite" className="text-xs text-muted">
        {status || tx.note}
      </span>
    </div>
  );
}
