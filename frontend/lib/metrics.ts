import { egp, num, pct } from "./format";
/** The metrics the time machine and investigation views can show. `agg`: how to combine months in a before/after window. */
export type MetricDef = { key: string; label: string; unit: string; agg: "sum" | "avg" | "last"; fmt: (v: number) => string; group: "sales" | "stock" | "production" | "marketing" };
export const METRICS: MetricDef[] = [
  { key: "net_sales_egp", label: "Net sales", unit: "EGP", agg: "sum", fmt: (v) => egp(v), group: "sales" },
  { key: "units_sold", label: "Units sold", unit: "units", agg: "sum", fmt: (v) => num(v), group: "sales" },
  { key: "gross_profit_egp", label: "Gross profit", unit: "EGP", agg: "sum", fmt: (v) => egp(v), group: "sales" },
  { key: "refunds_egp", label: "Refunds", unit: "EGP", agg: "sum", fmt: (v) => egp(v), group: "sales" },
  { key: "returned_lines", label: "Returned sale lines", unit: "lines", agg: "sum", fmt: (v) => num(v), group: "sales" },
  { key: "closing_stock_units", label: "Closing stock", unit: "units", agg: "last", fmt: (v) => num(v), group: "stock" },
  { key: "stockout_days", label: "Stock-out days", unit: "days", agg: "sum", fmt: (v) => num(v), group: "stock" },
  { key: "units_produced", label: "Units produced", unit: "units", agg: "sum", fmt: (v) => num(v), group: "production" },
  { key: "units_rejected", label: "Units rejected", unit: "units", agg: "sum", fmt: (v) => num(v), group: "production" },
  { key: "avg_efficiency_pct", label: "Production efficiency", unit: "%", agg: "avg", fmt: (v) => `${num(v, 1)}%`, group: "production" },
  { key: "campaign_spend_egp", label: "Campaign spend", unit: "EGP", agg: "sum", fmt: (v) => egp(v), group: "marketing" },
];
export const METRIC = Object.fromEntries(METRICS.map((m) => [m.key, m]));
export const addMonths = (m: string, n: number) => { const [y, mo] = m.split("-").map(Number); const d = new Date(Date.UTC(y, mo - 1 + n, 1)); return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`; };
/** Aggregate one metric over a list of month rows. Returns null when no month has the metric (so "no data" is never shown as zero). */
export function aggregate(rows: any[], m: MetricDef) {
  const v = rows.map((r) => r[m.key]).filter((x) => x != null) as number[]; if (!v.length) return { value: null as number | null, months: 0 };
  const value = m.agg === "sum" ? v.reduce((a, b) => a + b, 0) : m.agg === "avg" ? v.reduce((a, b) => a + b, 0) / v.length : v[v.length - 1];
  return { value, months: v.length };
}
/** Before/after around a pivot month: `n` months before (excluding the pivot) against the pivot and `n - 1` months after. */
export function beforeAfter(months: any[], pivot: string, n: number, m: MetricDef) {
  const b = months.filter((r) => r.month >= addMonths(pivot, -n) && r.month < pivot); const a = months.filter((r) => r.month >= pivot && r.month < addMonths(pivot, n));
  const B = aggregate(b, m), A = aggregate(a, m);
  const change = B.value != null && A.value != null ? A.value - B.value : null; const rel = change != null && B.value ? change / Math.abs(B.value) : null;
  return { before: B, after: A, change, rel, partial: B.months < n || A.months < n };
}
export { pct };
