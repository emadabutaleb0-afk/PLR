"use client";
import { i18nState } from "./i18n";
export class ApiError extends Error { status: number; code?: string; constructor(m: string, s: number, c?: string) { super(m); this.status = s; this.code = c; } }
const KEY = "mb_tokens";
const safe = <T,>(f: () => T, d: T): T => { try { return f(); } catch { return d; } };
export const tokens = {
  get: () => (typeof window === "undefined" ? null : safe(() => JSON.parse(localStorage.getItem(KEY) || "null"), null)),
  set: (t: any) => safe(() => localStorage.setItem(KEY, JSON.stringify(t)), undefined),
  clear: () => safe(() => localStorage.removeItem(KEY), undefined),
};
const MSG = {
  en: { network: "We could not reach the server. Check that the backend is running, then retry.", generic: "Something went wrong. Please try again." },
  ar: { network: "تعذّر الاتصال بالخادم. تأكد أن الباك إند يعمل ثم أعد المحاولة.", generic: "حدث خطأ ما. من فضلك حاول مرة أخرى." },
};
const m = () => MSG[i18nState.lang];
let refreshing: Promise<boolean> | null = null;
async function refresh(): Promise<boolean> {
  const t = tokens.get(); if (!t?.refresh_token) return false;
  refreshing ??= fetch("/api/v1/auth/refresh", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh_token: t.refresh_token }) })
    .then(async (r) => { if (!r.ok) return false; tokens.set(await r.json()); return true; }).catch(() => false).finally(() => { refreshing = null; });
  return refreshing;
}
export async function api<T = any>(path: string, opts: RequestInit & { raw?: boolean } = {}): Promise<T> {
  const isFormData = typeof FormData !== "undefined" && opts.body instanceof FormData;
  const defHeaders: Record<string, string> = { "Accept-Language": i18nState.lang, ...(tokens.get()?.access_token ? { Authorization: `Bearer ${tokens.get().access_token}` } : {}) };
  if (!isFormData) defHeaders["Content-Type"] = "application/json";
  const doFetch = () => fetch(`/api/v1${path}`, { ...opts, headers: { ...defHeaders, ...(opts.headers || {}) } });
  let r = await doFetch().catch(() => { throw new ApiError(m().network, 0, "network"); });
  const isAuthCall = path.startsWith("/auth/login") || path.startsWith("/auth/refresh");
  if (r.status === 401 && !isAuthCall && (await refresh())) r = await doFetch();
  if (r.status === 401 && !isAuthCall) { tokens.clear(); if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) window.location.href = "/login"; }
  if (!r.ok) {
    let msg = m().generic, code: string | undefined;
    try { const j = await r.json(); msg = j.error?.message || msg; code = j.error?.code; } catch {}
    throw new ApiError(msg, r.status, code);
  }
  if (opts.raw) return r as any;
  return r.json();
}
export async function download(path: string, filename: string) {
  const r: Response = await api(path, { raw: true } as any);
  const b = await r.blob(); const a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = filename; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
