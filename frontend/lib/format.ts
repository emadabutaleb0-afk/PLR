import { i18nState } from "./i18n";
const ar = () => i18nState.lang === "ar";
/** Money in EGP. English: "EGP 1.2M". Arabic: "1.2 مليون ج.م". Digits stay Western (the usual business convention in Egypt). */
export const egp = (v: number | null | undefined, compact = true) => {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const a = Math.abs(v);
  if (ar()) {
    if (compact && a >= 1e6) return `${(v / 1e6).toFixed(a >= 1e7 ? 1 : 2)} مليون ج.م`;
    if (compact && a >= 1e4) return `${(v / 1e3).toFixed(0)} ألف ج.م`;
    return `${Math.round(v).toLocaleString("en-US")} ج.م`;
  }
  if (compact && a >= 1e6) return `EGP ${(v / 1e6).toFixed(a >= 1e7 ? 1 : 2)}M`;
  if (compact && a >= 1e4) return `EGP ${(v / 1e3).toFixed(0)}K`;
  return `EGP ${Math.round(v).toLocaleString("en-US")}`;
};
export const pct = (v: number | null | undefined, d = 1) => (v === null || v === undefined || Number.isNaN(v) ? "—" : `${(v * 100).toFixed(d)}%`);
export const num = (v: number | null | undefined, d = 0) => (v === null || v === undefined || Number.isNaN(v) ? "—" : v.toLocaleString("en-US", { maximumFractionDigits: d }));
export const greetingKey = () => { const h = new Date().getHours(); return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening"; };
/** Chart axis ticks, language aware: 1.5M / 1.5 مليون */
export const axisM = (v: number, d = 0) => (ar() ? `${(v / 1e6).toFixed(d)} م` : `${(v / 1e6).toFixed(d)}M`);
export const axisK = (v: number) => (ar() ? `${(v / 1e3).toFixed(0)} ألف` : `${(v / 1e3).toFixed(0)}K`);
export const ACTION_KEYS: Record<string, string> = { SCALE: "Scale", MAINTAIN: "Maintain", REPLENISH: "Replenish", RELOCATE: "Transfer", DISCOUNT: "Discount", FIX: "Fix", STOP_REPLENISHMENT: "Stop replenishing", PHASE_OUT: "Phase out" };
/** Kept for compatibility: English labels. Use t(ACTION_LABEL[x]) in components. */
export const ACTION_LABEL = ACTION_KEYS;
export const RISK_TEXT: Record<string, string> = { HIGH: "High stockout risk — likely to run out before new stock arrives", MEDIUM: "Watch — close to the reorder point", LOW: "Healthy" };
export const DEAD_TEXT: Record<string, string> = { HIGH: "High dead-stock risk — unlikely to sell at the current pace", MEDIUM: "Slow — building up", LOW: "Healthy" };
