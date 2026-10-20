// UI text in English and Bengali. Add a key to both languages; missing Bengali falls back to English.

export type Lang = "en" | "bn";

const en = {
  "brand.tagline": "Trust less, Verify more.",
  "nav.crashTest": "Crash-Test",
  "nav.replay": "Replay",
  "nav.radar": "Radar",
  "nav.pricing": "Pricing",
  "nav.docs": "Docs",
  "nav.login": "Log in",
  "nav.dashboard": "Dashboard",
  "theme.dark": "Dark",
  "theme.paper": "Paper",
  "theme.toggle": "Switch theme",
  "lang.toggle": "বাংলা",
  "status.checking": "Checking server...",
  "status.live": "Live analysis available",
  "status.demo": "Demo mode: precomputed results",
  "status.offline": "Server waking up or offline",
  "hero.title": "Trust less, Verify more.",
  "hero.subtitle": "Before you sign, invest or partner, see what the evidence really says.",
  "hero.cta": "Run a Crash-Test",
  "hero.demo": "Try the demo, no sign-up",
  "hero.plans": "See plans",
  "hero.point1": "Source-cited findings",
  "hero.point2": "Gaps shown, never hidden",
  "hero.point3": "Self-checking AI",
};

export type Key = keyof typeof en;

const bn: Partial<Record<Key, string>> = {
  "brand.tagline": "কম বিশ্বাস, বেশি যাচাই।",
  "nav.crashTest": "ক্র্যাশ-টেস্ট",
  "nav.replay": "রিপ্লে",
  "nav.radar": "রেডার",
  "nav.pricing": "মূল্য",
  "nav.docs": "ডকস",
  "nav.login": "লগ ইন",
  "nav.dashboard": "ড্যাশবোর্ড",
  "theme.dark": "ডার্ক",
  "theme.paper": "পেপার",
  "theme.toggle": "থিম বদলান",
  "lang.toggle": "English",
  "status.checking": "সার্ভার যাচাই হচ্ছে...",
  "status.live": "লাইভ বিশ্লেষণ চালু",
  "status.demo": "ডেমো মোড: আগে থেকে তৈরি ফলাফল",
  "status.offline": "সার্ভার চালু হচ্ছে বা বন্ধ",
  "hero.title": "কম বিশ্বাস, বেশি যাচাই।",
  "hero.subtitle": "চুক্তি, বিনিয়োগ বা অংশীদারিত্বের আগে জেনে নিন, প্রমাণ আসলে কী বলে।",
  "hero.cta": "ক্র্যাশ-টেস্ট চালান",
  "hero.demo": "ডেমো দেখুন, সাইন আপ ছাড়াই",
  "hero.plans": "প্ল্যান দেখুন",
  "hero.point1": "প্রতিটি ফলাফলে উৎস",
  "hero.point2": "ঘাটতি লুকানো হয় না",
  "hero.point3": "নিজেকে যাচাই করে এমন এআই",
};

export const dict: Record<Lang, Partial<Record<Key, string>>> = { en, bn };

export function translate(lang: Lang, key: Key): string {
  return dict[lang][key] ?? en[key];
}