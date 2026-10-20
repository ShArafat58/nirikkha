// Sample responses for NEXT_PUBLIC_USE_MOCK=true, so the UI works without the backend.
import type { MeResponse, Plan, Status } from "./api";

export const MOCK_STATUS: Status = { live_mode: "worker", worker_online: false, worker: null, rerank_enabled: null };

export const MOCK_QUESTIONS = [
  "What was the name of your first school?",
  "In which city were you born?",
  "What was the name of your first pet?",
  "What is the title of your favourite book?",
  "What was the model of your first mobile phone?",
];

export const MOCK_PLANS: Plan[] = [
  { id: "free", name: "Free", audience: "Students, individual investors, trials", price_usd: 0, price_unit: "month",
    price_label: "$0", crash_tests_per_month: 3, radar_companies: 0,
    features: ["3 Crash-Tests per month", "Summary report", "Evidence links to SEC filings"] },
  { id: "analyst_pro", name: "Analyst Pro", audience: "Individual analysts, small funds", price_usd: 49,
    price_unit: "user / month", price_label: "$49 per user / month", crash_tests_per_month: 30, radar_companies: 10,
    features: ["30 Crash-Tests per month", "Full evidence and Rule Engine results", "PDF export",
               "Regulatory Radar alerts for 10 companies"] },
  { id: "team", name: "Team", audience: "Research and compliance teams (up to 5 users)", price_usd: 399,
    price_unit: "month", price_label: "$399 / month", crash_tests_per_month: 150, radar_companies: 50,
    features: ["150 Crash-Tests per month", "Shared workspace", "Decision workflow", "Audit trail",
               "Regulatory Radar for 50 companies"] },
  { id: "enterprise", name: "Enterprise", audience: "Banks, institutional investors, large compliance teams",
    price_usd: null, price_unit: "year", price_label: "Annual contract", crash_tests_per_month: null,
    radar_companies: null, features: ["Approved private documents", "Runs on your own servers (data stays inside)",
                                      "Custom rules", "SSO", "Unlimited use"] },
];

export const MOCK_ME: MeResponse = {
  user: { id: "mock-demo", email: "demo@nirikkha.demo", name: "Demo reviewer", organization: "Nirikkha demo",
          job_role: "Judge / reviewer", role: "demo", plan: "free", created_at: new Date().toISOString() },
  usage: { used_this_month: 0, limit: null, unlimited: true, remaining: null },
};