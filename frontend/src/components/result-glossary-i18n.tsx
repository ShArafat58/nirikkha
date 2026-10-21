"use client";

import ResultGlossary, { type GlossaryItem } from "./result-glossary";
import { useApp } from "./providers";

const BN_ITEMS: GlossaryItem[] = [
  { term: "Pass", text: "উপলভ্য প্রমাণ নিয়মের শর্ত পূরণ করে।", tone: "pass" },
  {
    term: "Potential Gap",
    text: "প্রমাণে একটি সম্ভাব্য দুর্বলতা দেখা যাচ্ছে, যা একজন মানুষের পর্যালোচনা করা দরকার। এটি অন্যায়ের প্রমাণ নয়।",
    tone: "gap",
  },
  {
    term: "Fail",
    text: "যথেষ্ট ও প্রযোজ্য প্রমাণ দেখাচ্ছে যে শর্তটি পূরণ হয়নি।",
    tone: "fail",
  },
  {
    term: "Insufficient Evidence",
    text: "প্রকাশ্য ফাইলিংয়ে নির্ভরযোগ্য সিদ্ধান্তের মতো তথ্য নেই। এটি কখনো কম ঝুঁকি হিসেবে গোনা হয় না।",
    tone: "insufficient",
  },
  {
    term: "Risk Severity বনাম Evidence Confidence",
    text: "Severity মানে সমস্যাটি কত গুরুতর হতে পারে। Confidence মানে প্রমাণ কত শক্ত। দুটো আলাদা দেখানো হয়।",
    tone: "info",
  },
  {
    term: "প্রযোজ্য নয়",
    text: "নিয়মটি এই কোম্পানির জন্য প্রযোজ্য নয়, যেমন টেকনোলজি কোম্পানির জন্য শুধু-ব্যাংকের নিয়ম।",
    tone: "info",
  },
  {
    term: "Reliability Sentinel",
    text: "দ্বিতীয় একটি মডেল প্রতিটি AI ফলাফল তার উদ্ধৃত অংশের সাথে মিলিয়ে দেখে এবং সন্দেহজনকগুলো মানুষের পর্যালোচনায় পাঠায়।",
    tone: "info",
  },
  {
    term: "Health Score",
    text: "০ থেকে ১০০-এর একটি সারাংশ। প্রতিটি কাটা নম্বর তার কারণ হওয়া ফলাফলসহ দেখানো হয়।",
    tone: "info",
  },
];

export default function ResultGlossaryI18n() {
  const { lang } = useApp();
  return (
    <div className="mt-16">
      {lang === "bn" ? (
        <ResultGlossary
          title="রিপোর্ট কীভাবে পড়বেন"
          subtitle="প্রতিটি নিরীক্ষা রিপোর্টে ব্যবহৃত শব্দ ও ফলাফলের ধরনের ব্যাখ্যা।"
          items={BN_ITEMS}
        />
      ) : (
        <ResultGlossary />
      )}
    </div>
  );
}
