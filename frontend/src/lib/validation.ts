// Client-side checks that mirror the backend (the backend stays the authority).

export const PASSWORD_RULES = [
  { key: "min_length", test: (p: string) => p.length >= 8 },
  { key: "upper", test: (p: string) => /[A-Z]/.test(p) },
  { key: "lower", test: (p: string) => /[a-z]/.test(p) },
  { key: "digit", test: (p: string) => /\d/.test(p) },
] as const;

export function passwordOk(password: string): boolean {
  return password.length <= 128 && PASSWORD_RULES.every((rule) => rule.test(password));
}

export function isAdult(dob: string, today: Date = new Date()): boolean {
  const parts = dob.split("-").map(Number);
  if (parts.length !== 3 || parts.some(Number.isNaN)) return false;
  const [y, m, d] = parts;
  let age = today.getFullYear() - y;
  if (today.getMonth() + 1 < m || (today.getMonth() + 1 === m && today.getDate() < d)) age -= 1;
  return age >= 18 && age <= 120;
}

export function maxBirthDate(today: Date = new Date()): string {
  const d = new Date(today);
  d.setFullYear(d.getFullYear() - 18);
  return d.toISOString().slice(0, 10);
}

// Only allow same-site paths after login (no open redirects).
export function safeNext(raw: string | null, fallback = "/dashboard"): string {
  return raw && raw.startsWith("/") && !raw.startsWith("//") ? raw : fallback;
}