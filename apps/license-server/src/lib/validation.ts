// Phase L1a — Input validation helpers. Hand-rolled to keep the bundle
// tiny (no zod) — the Worker free tier has tight CPU + startup budgets.

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export type ValidationError = { field: string; message: string };

export function isEmail(v: unknown): v is string {
  return typeof v === "string" && v.length <= 254 && EMAIL_RE.test(v);
}

export function isStrongPassword(v: unknown): v is string {
  if (typeof v !== "string") return false;
  if (v.length < 10 || v.length > 256) return false;
  if (!/\d/.test(v)) return false;
  return true;
}

export function isDisplayName(v: unknown): v is string {
  return (
    typeof v === "string" && v.trim().length >= 1 && v.length <= 100
  );
}

export function normaliseEmail(v: string): string {
  return v.trim().toLowerCase();
}

export interface SignupBody {
  email: string;
  password: string;
  display_name: string;
  device_id?: string;
  device_label?: string;
}

export function validateSignup(body: unknown): {
  ok: true;
  value: SignupBody;
} | { ok: false; errors: ValidationError[] } {
  const errors: ValidationError[] = [];
  const b = (body && typeof body === "object" ? body : {}) as Record<string, unknown>;
  if (!isEmail(b.email)) errors.push({ field: "email", message: "Invalid email." });
  if (!isStrongPassword(b.password))
    errors.push({
      field: "password",
      message: "Password must be at least 10 characters and contain a digit.",
    });
  if (!isDisplayName(b.display_name))
    errors.push({ field: "display_name", message: "Display name must be 1-100 characters." });
  if (errors.length) return { ok: false, errors };
  return {
    ok: true,
    value: {
      email: normaliseEmail(b.email as string),
      password: b.password as string,
      display_name: (b.display_name as string).trim(),
      device_id: typeof b.device_id === "string" ? b.device_id : undefined,
      device_label: typeof b.device_label === "string" ? b.device_label : undefined,
    },
  };
}

export interface LoginBody {
  email: string;
  password: string;
  device_id?: string;
  device_label?: string;
}

export function validateLogin(body: unknown): { ok: true; value: LoginBody } | { ok: false; errors: ValidationError[] } {
  const errors: ValidationError[] = [];
  const b = (body && typeof body === "object" ? body : {}) as Record<string, unknown>;
  if (!isEmail(b.email)) errors.push({ field: "email", message: "Invalid email." });
  if (typeof b.password !== "string" || !b.password.length)
    errors.push({ field: "password", message: "Password required." });
  if (errors.length) return { ok: false, errors };
  return {
    ok: true,
    value: {
      email: normaliseEmail(b.email as string),
      password: b.password as string,
      device_id: typeof b.device_id === "string" ? b.device_id : undefined,
      device_label: typeof b.device_label === "string" ? b.device_label : undefined,
    },
  };
}
