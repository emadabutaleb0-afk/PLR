"use client";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, Tooltip, XAxis, YAxis } from "recharts";
import { useApi } from "@/lib/hooks";
import { egp, pct, num, axisK } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { Page, Panel, Stat } from "@/components/Page";
import { ChartBox, axis } from "@/components/Chart";
import { ErrorState, LoadingBlock } from "@/components/States";
export default function Ops() {
  const { t } = useI18n(); const { data: d, error, isLoading, refetch } = useApi("/operations/bottlenecks");
  if (error) return <ErrorState error={error} retry={refetch} />; if (isLoading || !d) return <LoadingBlock />;
  const k = d.kpis;
  return <Page title="Operations Control" sub="Production, bottlenecks, machines and printing." fresh={d.freshness}>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5"><Stat label="Production efficiency (90d)" value={`${k.efficiency_90d}%`} /><Stat label="Avg delay (days)" value={k.delay_90d} /><Stat label="Rejected production" value={pct(k.reject_rate_90d)} /><Stat label="Unplanned downtime (h)" value={num(k.unplanned_downtime_90d)} /><Stat label="Printing rework" value={egp(k.printing_rework_90d)} /></div>
    <div className="grid gap-4 xl:grid-cols-2"><Panel title="Bottlenecks" hint="Delay days by primary bottleneck"><ChartBox h={250}><BarChart data={d.bottlenecks}><CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" /><XAxis dataKey="bottleneck" tick={axis} /><YAxis tick={axis} /><Tooltip /><Bar dataKey="delay_days" name={t("Delay days")} fill="var(--series-ink)" /></BarChart></ChartBox></Panel>
      <Panel title="Efficiency & rejects by month"><ChartBox h={250}><LineChart data={(d.monthly || []).slice(-24)}><CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" /><XAxis dataKey="month" tick={axis} /><YAxis yAxisId="a" tick={axis} /><YAxis yAxisId="b" orientation="right" tick={axis} tickFormatter={(v) => pct(v, 1)} /><Tooltip /><Legend /><Line yAxisId="a" dataKey="efficiency" name={t("Efficiency %")} stroke="var(--c-green)" dot={false} /><Line yAxisId="b" dataKey="reject_rate" name={t("Reject rate")} stroke="var(--c-red)" dot={false} /></LineChart></ChartBox></Panel>
      <Panel title="Machine downtime (unplanned hours)"><ChartBox h={250}><BarChart data={(d.machines || []).slice(0, 12)}><CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" /><XAxis dataKey="machine_id" tick={axis} /><YAxis tick={axis} /><Tooltip /><Bar dataKey="unplanned_hours" name={t("Unplanned hours")} fill="var(--c-amber)" /></BarChart></ChartBox></Panel>
      <Panel title="Printing rework by machine"><ChartBox h={250}><BarChart data={d.printing}><CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" /><XAxis dataKey="machine_id" tick={axis} /><YAxis tick={axis} tickFormatter={(v) => axisK(v)} /><Tooltip formatter={(v: any) => egp(v, false)} /><Bar dataKey="rework_cost" name={t("Rework cost")} fill="var(--c-red)" /></BarChart></ChartBox></Panel></div>
    {d.downtime_link && <Panel title="Does downtime explain the delays?" hint="Unplanned downtime hours vs delay days caused by each stage"><div className="grid gap-4 lg:grid-cols-[1fr_1.3fr]"><div className="rounded-xl bg-slate-50 p-4"><p className="text-xs text-slate-500">{t("Monthly correlation")} ({d.downtime_link.months} {t("months")})</p><p className="text-3xl font-semibold">{d.downtime_link.correlation ?? "—"}</p><p className="mt-2 text-sm text-slate-600">{d.downtime_link.verdict}</p><p className="mt-2 text-xs text-slate-500">{d.downtime_link.note}</p></div>
      <table className="w-full text-sm"><thead className="text-xs uppercase text-slate-500"><tr><th className="py-2 text-start">{t("Stage")}</th><th className="text-end">{t("Unplanned downtime (h)")}</th><th className="text-end">{t("Delay days as bottleneck")}</th></tr></thead><tbody className="divide-y divide-slate-100">{d.downtime_link.stages.map((x: any) => <tr key={x.stage}><td className="py-2">{x.stage}</td><td className="text-end">{num(x.unplanned_downtime_hours, 0)}</td><td className="text-end font-medium">{num(x.bottleneck_delay_days, 0)}</td></tr>)}</tbody></table></div></Panel>}
  </Page>;
}
