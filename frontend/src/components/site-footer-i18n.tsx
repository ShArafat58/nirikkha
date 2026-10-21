"use client";

import SiteFooter, { type SiteFooterLabels } from "./site-footer";
import { useApp } from "./providers";

const BN: Partial<SiteFooterLabels> = {
  productName: "নিরীক্ষা",
  tagline: "কম বিশ্বাস, বেশি যাচাই।",
  builtLine:
    "GovernanceIQ চ্যালেঞ্জের জন্য তৈরি, International AI Builders Congress 2026।",
  productHeading: "প্রোডাক্ট",
  learnHeading: "জানুন",
  responsibleHeading: "দায়িত্বশীল ব্যবহার",
  responsibleText:
    "নিরীক্ষা কোনো কোম্পানিকে অভিযুক্ত করে না। ফলাফলগুলো যাচাই করার প্রশ্ন, প্রমাণ নয়। এটি আইনি বা বিনিয়োগ পরামর্শ নয়।",
  copyright: "© ২০২৬ নিরীক্ষা",
  evidenceLine: "শুধু প্রকাশ্য SEC ফাইলিং · প্রমাণ আগে",
  productNavLabel: "প্রোডাক্টের লিংক",
  learnNavLabel: "জানার লিংক",
  githubLinkLabel: "GitHub-এ নিরীক্ষা (নতুন ট্যাবে খোলে)",
  links: {
    crashTest: "ক্র্যাশ-টেস্ট",
    reports: "রিপোর্ট",
    replay: "রিপ্লে",
    graph: "গ্রাফ",
    radar: "রেডার",
    pricing: "মূল্য",
    docs: "ডকস",
    github: "GitHub",
  },
};

export default function SiteFooterI18n() {
  const { lang } = useApp();
  return (
    <div className="print:hidden">
      <SiteFooter labels={lang === "bn" ? BN : undefined} />
    </div>
  );
}
