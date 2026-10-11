"use client";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Legend, Line, LineChart, Tooltip, XAxis, YAxis } from "recharts";
import { useApi } from "@/lib/hooks";
import { egp, pct, axisM } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { Page, Panel } from "@/components/Page";
import { ChartBox, axis } from "@/components/Chart";
import { KpiCard } from "@/components/Cards";
import { ErrorState, LoadingGrid, LoadingBlock } from "@/components/States";
import { Badge } from "@/components/ui/primitives";
export default function Dashboard() {
  const { t } = useI18n(); const { data, error, isLoading, refetch } = useApi("/executive/overview");
  if (error) return <ErrorState error={error} retry={refetch} />;
  if (isLoading || !data) return <><LoadingGrid n={8} /><div className="mt-6"><LoadingBlock /></div></>;
  const tr = (data.trend || []).slice(-24);
  const rc = (data.recovery_by_category || []).slice(0, 8).map((x: any) => ({ ...x, label: t(x.category) }));
  return <Page title="Executive Dashboard" sub={data.period_label} fresh={data.freshness}>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">{data.kpis.map((k: any) => <KpiCard key={k.key} k={k} />)}</div>
    <div className="grid gap-4 xl:grid-cols-2">
      <Panel title="Revenue vs Profit" hint="Monthly net sales and gross profit"><ChartBox><AreaChart data={tr}><CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" /><XAxis dataKey="month" tick={axis} /><YAxis tick={axis} tickFormatter={(v) => axisM(v)} /><Tooltip formatter={(v: any) => egp(v, false)} /><Legend />
        <Area dataKey="net" name={t("Revenue")} stroke="var(--series-ink)" fill="var(--c-soft)" /><Area dataKey="gp" name={t("Gross profit")} stroke="var(--c-green)" fill="var(--c-green-soft)" /></AreaChart></ChartBox></Panel>
      <Panel title="Margin Trend" hint="Gross margin by month"><ChartBox><LineChart data={tr}><CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" /><XAxis dataKey="month" tick={axis} /><YAxis tick={axis} tickFormatter={(v) => pct(v, 1)} domain={["auto", "auto"]} /><Tooltip formatter={(v: any) => pct(v)} /><Line dataKey="margin" name={t("Gross margin")} stroke="var(--c-amber)" strokeWidth={2} dot={false} /></LineChart></ChartBox></Panel>
      <Panel title="Inventory Risk" hint="Stock lines by health, per location"><ChartBox><BarChart data={data.inventory_by_location}><CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" /><XAxis dataKey="location_name" tick={axis} /><YAxis tick={axis} /><Tooltip /><Legend />
        <Bar dataKey="healthy" name={t("Healthy")} stackId="a" fill="var(--c-green)" /><Bar dataKey="stockout_medium" name={t("Stockout watch")} stackId="a" fill="var(--c-amber)" /><Bar dataKey="stockout_high" name={t("High stockout risk")} stackId="a" fill="var(--c-red)" /><Bar dataKey="dead_medium" name={t("Slow stock")} stackId="a" fill="var(--c-violet-soft)" /><Bar dataKey="dead_high" name={t("High dead-stock risk")} stackId="a" fill="var(--c-violet)" /></BarChart></ChartBox></Panel>
      <Panel title="Recovery Opportunity" hint="Estimated value of open decisions by type (estimates)"><ChartBox><BarChart data={rc} layout="vertical"><CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" /><XAxis type="number" tick={axis} tickFormatter={(v) => axisM(v, 1)} /><YAxis dataKey="label" type="category" width={150} tick={axis} /><Tooltip formatter={(v: any) => egp(v, false)} /><Bar dataKey="value" name={t("Estimated value")} fill="var(--series-ink)" radius={[0, 6, 6, 0]} /></BarChart></ChartBox></Panel></div>
    <Panel title="Top Product Decisions"><div className="divide-y divide-slate-100">{data.top_decisions.map((d: any) => <div key={d.rec_key} className="flex items-center justify-between gap-3 py-2.5 text-sm"><span className="font-medium">{d.title}</span><span className="flex items-center gap-3"><Badge kind={d.urgency}>{t(d.urgency)}</Badge><span className="w-24 text-end font-semibold text-emerald-600">{egp(d.value)}</span></span></div>)}</div></Panel>
  </Page>;
}
