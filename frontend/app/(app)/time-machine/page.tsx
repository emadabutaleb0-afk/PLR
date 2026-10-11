"use client";
import { Suspense, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Bar, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useApi } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n";
import { METRIC, METRICS, addMonths, beforeAfter } from "@/lib/metrics";
import { egp, pct } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Page, Panel } from "@/components/Page";
import { ProductPicker } from "@/components/ProductPicker";
import { axis } from "@/components/Chart";
import { Badge, Card, Select } from "@/components/ui/primitives";
import { Empty, ErrorState, LoadingBlock } from "@/components/States";
import { Tabs } from "@/components/ui/layout";

const MARK_COLOR: Record<string, string> = { approval: "var(--c-green)", execution: "var(--c-sky)", outcome: "var(--series-gold)", data_refresh: "var(--c-muted)", campaign_start: "var(--c-violet)", campaign_end: "var(--c-violet-soft)" };
const MARK_LABEL: Record<string, string> = { approval: "Decision approved", execution: "Execution recorded", outcome: "Outcome measured", data_refresh: "Data refresh", campaign_start: "Campaign starts", campaign_end: "Campaign ends" };

function Machine() {
  const { t } = useI18n(); const sp = useSearchParams(); const router = useRouter();
  const product = sp.get("product"); const location = sp.get("location") || ""; const [since, setSince] = useState(""); const [until, setUntil] = useState("");
  const [pivot, setPivot] = useState<string | null>(null); const [win, setWin] = useState(3); const [name, setName] = useState<string | null>(null); const [kinds, setKinds] = useState<string[]>(["approval", "execution", "outcome", "data_refresh"]); const [tab, setTab] = useState<"sales" | "stock" | "production">("sales");
  const opts = useApi<any>("/workspace/scope-options");
  const qs = new URLSearchParams(); if (product) qs.set("product_id", product); if (location) qs.set("location_id", location); if (since) qs.set("since", since); if (until) qs.set("until", until);
  const q = useApi<any>(`/workspace/timeline?${qs}`);
  const set = (k: string, v: string | null) => { const p = new URLSearchParams(sp.toString()); v ? p.set(k, v) : p.delete(k); router.replace(`/time-machine?${p}`); };
  const d = q.data; const months: any[] = d?.months || [];
  const marks = useMemo(() => (d?.markers || []).filter((m: any) => kinds.includes(m.kind)), [d, kinds]);
  const monthMarks = useMemo(() => { const o: Record<string, any[]> = {}; marks.forEach((m: any) => (o[m.month] ||= []).push(m)); return o; }, [marks]);
  const cur = pivot && months.some((m) => m.month === pivot) ? pivot : null;
  const present = (k: string) => d && d.coverage[k];
  const Chart = ({ keys, bars }: { keys: string[]; bars?: string[] }) => <div className="chart-ltr h-72 w-full"><ResponsiveContainer><ComposedChart data={months} syncId="tm" onClick={(e: any) => e?.activeLabel && setPivot(e.activeLabel)} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
    <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" /><XAxis dataKey="month" tick={axis} minTickGap={24} /><YAxis yAxisId="l" tick={axis} width={56} tickFormatter={(v) => (Math.abs(v) >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : Math.abs(v) >= 1e3 ? `${(v / 1e3).toFixed(0)}K` : String(v))} />
    <YAxis yAxisId="r" orientation="right" tick={axis} width={44} hide={!keys.some((k) => !bars?.includes(k) && METRIC[k].unit !== METRIC[keys[0]].unit)} />
    <Tooltip content={({ active, payload, label }: any) => !active || !payload?.length ? null : <div className="recharts-default-tooltip p-3 text-xs"><p className="font-semibold">{label}</p>{payload.map((p: any) => <p key={p.dataKey} className="tabular"><span style={{ color: p.color }}>●</span> {t(METRIC[p.dataKey].label)}: <b>{METRIC[p.dataKey].fmt(p.value)}</b> <span className="text-slate-500">({METRIC[p.dataKey].unit})</span></p>)}
      {(monthMarks[label] || []).slice(0, 4).map((m: any, i: number) => <p key={i} className="mt-1 text-slate-500">◆ {m.label}</p>)}<p className="mt-1 text-slate-500">{t("Click to set the comparison point")}</p></div>} />
    <Legend formatter={(v) => t(METRIC[v]?.label || v)} />
    {keys.map((k, i) => bars?.includes(k) ? <Bar key={k} yAxisId="l" dataKey={k} fill={i === 0 ? "var(--series-gold)" : "var(--c-muted)"} radius={[4, 4, 0, 0]} maxBarSize={22} isAnimationActive={false} /> : <Line key={k} yAxisId={METRIC[k].unit === METRIC[keys[0]].unit ? "l" : "r"} dataKey={k} stroke={i === 1 ? "var(--series-ink)" : "var(--c-sky)"} strokeWidth={2} dot={false} connectNulls={false} isAnimationActive={false} />)}
    {Object.entries(monthMarks).filter(([m]) => months.some((r) => r.month === m)).map(([m, ms]) => <ReferenceLine key={m} yAxisId="l" x={m} stroke={MARK_COLOR[ms[0].kind]} strokeDasharray="2 3" strokeOpacity={0.8} />)}
    {cur && <ReferenceLine yAxisId="l" x={cur} stroke="var(--c-red)" strokeWidth={2} label={{ value: t("Compare from here"), position: "insideTopRight", fill: "var(--chart-axis)", fontSize: 11 }} />}</ComposedChart></ResponsiveContainer></div>;
  if (q.error) return <ErrorState error={q.error} retry={q.refetch} />;
  const tabs = [{ key: "sales" as const, label: "Sales" }, { key: "stock" as const, label: "Inventory" }, ...(present("units_produced") ? [{ key: "production" as const, label: "Production" }] : [])];
  return <div className="space-y-4">
    <Card className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-[2fr_1fr_1fr_1fr]">
      <div><span className="mb-1 block text-xs font-medium text-slate-600">{t("Product (optional)")}</span><ProductPicker value={product} label={name} onPick={(id, n) => { setName(n || null); set("product", id); }} placeholder={t("All products in your scope")} /></div>
      <label className="text-xs font-medium text-slate-600">{t("Location")}<Select className="mt-1 h-10 w-full" value={location} onChange={(e) => set("location", e.target.value || null)}><option value="">{t("All locations")}</option>{opts.data?.locations.map((l: any) => <option key={l.location_id} value={l.location_id}>{l.location_name}</option>)}</Select></label>
      <label className="text-xs font-medium text-slate-600">{t("From")}<input type="month" value={since} max={until || undefined} onChange={(e) => setSince(e.target.value)} className="mt-1 h-10 w-full rounded-xl border border-line bg-surface px-3 text-sm" /></label>
      <label className="text-xs font-medium text-slate-600">{t("To")}<input type="month" value={until} min={since || undefined} onChange={(e) => setUntil(e.target.value)} className="mt-1 h-10 w-full rounded-xl border border-line bg-surface px-3 text-sm" /></label></Card>
    {q.isLoading || !d ? <LoadingBlock h="h-80" /> : !months.length ? <Empty title="No history for this selection" hint="The raw tables have no months for this product, location and date range." /> : <>
      <div className="rounded-xl bg-sunken p-3 text-xs text-slate-600"><p>{d.notes.map((n: string) => t(n)).join(" ")}</p>
        {!!d.unavailable.length && <p className="mt-1 font-medium">{t("History not available for")}: {d.unavailable.map((u: any) => t(METRIC[u.metric]?.label || u.metric)).join(", ")}.</p>}</div>
      <Panel title="Business history" hint="Monthly figures from the raw business tables. Click a month to compare before and after it. Dotted lines are recorded events.">
        <Tabs label="History view" tabs={tabs} value={tab} onChange={setTab} />
        <div className="pt-3">{tab === "sales" && <Chart keys={["net_sales_egp", ...(present("gross_profit_egp") ? ["gross_profit_egp"] : [])]} bars={["net_sales_egp"]} />}
          {tab === "stock" && <Chart keys={["closing_stock_units", "stockout_days"].filter(present)} bars={["closing_stock_units"]} />}
          {tab === "production" && <Chart keys={["units_produced", "units_rejected"].filter(present)} bars={["units_produced"]} />}</div>
        <div className="mt-3 flex flex-wrap items-center gap-2" role="group" aria-label={t("Event markers")}>{Object.keys(MARK_LABEL).map((k) => <button key={k} aria-pressed={kinds.includes(k)} onClick={() => setKinds((x) => x.includes(k) ? x.filter((y) => y !== k) : [...x, k])} className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium", kinds.includes(k) ? "border-line-strong bg-surface" : "border-line text-slate-400")}><span className="h-2 w-2 rounded-full" style={{ background: MARK_COLOR[k] }} />{t(MARK_LABEL[k])}<span className="tabular text-slate-500">{(d.markers || []).filter((m: any) => m.kind === k).length}</span></button>)}</div></Panel>
      <Panel title="Before and after" hint="Pick a month on the chart, then a window. Flows are summed, stock is the last month, efficiency is averaged. Months without data are never counted as zero.">
        <div className="mb-3 flex flex-wrap items-end gap-3"><label className="text-xs font-medium text-slate-600">{t("Comparison month")}<select value={cur || ""} onChange={(e) => setPivot(e.target.value || null)} className="mt-1 block h-9 rounded-xl border border-line bg-surface px-3 text-sm"><option value="">{t("Choose a month…")}</option>{months.map((m) => <option key={m.month}>{m.month}</option>)}</select></label>
          <label className="text-xs font-medium text-slate-600">{t("Window")}<select value={win} onChange={(e) => setWin(Number(e.target.value))} className="mt-1 block h-9 rounded-xl border border-line bg-surface px-3 text-sm">{[1, 3, 6, 12].map((n) => <option key={n} value={n}>{n} {t("months")}</option>)}</select></label>
          {cur && <p className="pb-2 text-xs text-slate-500">{addMonths(cur, -win)} → {addMonths(cur, -1)} {t("vs")} {cur} → {addMonths(cur, win - 1)}</p>}</div>
        {!cur ? <p className="text-sm text-slate-500">{t("Click a month on the chart or choose one above.")}</p> : <div className="overflow-x-auto"><table className="w-full text-sm"><caption className="sr-only">{t("Before and after comparison")}</caption><thead className="text-xs uppercase text-slate-500"><tr><th scope="col" className="p-2 text-start">{t("Metric")}</th><th scope="col" className="p-2 text-end">{t("Before")}</th><th scope="col" className="p-2 text-end">{t("After")}</th><th scope="col" className="p-2 text-end">{t("Change")}</th></tr></thead>
          <tbody className="divide-y divide-line">{METRICS.filter((m) => present(m.key)).map((m) => { const r = beforeAfter(months, cur, win, m); return <tr key={m.key}><th scope="row" className="p-2 text-start font-medium">{t(m.label)} <span className="text-xs font-normal text-slate-500">({m.unit})</span></th>
            <td className="num p-2 text-end">{r.before.value == null ? t("n/a") : m.fmt(r.before.value)}</td><td className="num p-2 text-end">{r.after.value == null ? t("n/a") : m.fmt(r.after.value)}</td>
            <td className="num p-2 text-end">{r.change == null ? "—" : <>{m.fmt(r.change)} {r.rel != null && <span className={cn("ms-1 text-xs", r.rel >= 0 ? "text-emerald-600" : "text-rose-600")}>{r.rel >= 0 ? "+" : ""}{pct(r.rel)}</span>}</>}{r.partial && <Badge kind="WATCH" className="ms-2">{t("partial window")}</Badge>}</td></tr>; })}</tbody></table>
          <p className="mt-3 text-xs text-slate-500">{t("A difference is not proof that one event caused it. For approved decisions the platform measures the effect against comparable untouched products on the Value Realization page.")}</p></div>}</Panel>
      <Panel title="Recorded events" hint="Only events that exist in the system.">{marks.length ? <ul className="divide-y divide-line text-sm">{marks.slice(-40).reverse().map((m: any, i: number) => <li key={i} className="flex items-center gap-3 py-2"><span className="h-2 w-2 shrink-0 rounded-full" style={{ background: MARK_COLOR[m.kind] }} /><span className="tabular w-24 shrink-0 text-xs text-slate-500">{m.date}</span><span className="min-w-0 flex-1 truncate">{m.label}</span><Badge kind="INFO">{t(MARK_LABEL[m.kind])}</Badge></li>)}</ul> : <p className="text-sm text-slate-500">{t("No recorded events match the selected types and range.")}</p>}</Panel></>}
  </div>;
}
export default function TimeMachine() { const f = useApi<any>("/workspace/timeline"); return <Page title="Business Time Machine" sub="Explore what really happened, month by month, and compare before and after any point." fresh={f.data?.freshness}><Suspense fallback={<LoadingBlock />}><Machine /></Suspense></Page>; }
