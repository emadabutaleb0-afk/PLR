"use client";
import { Bar, BarChart, CartesianGrid, Tooltip, XAxis, YAxis } from "recharts";
import { useApi } from "@/lib/hooks";
import { egp, pct, num, axisK } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { Page, Panel, Stat } from "@/components/Page";
import { ChartBox, axis } from "@/components/Chart";
import { ErrorState, LoadingBlock } from "@/components/States";
import { Badge } from "@/components/ui/primitives";
export default function Quality() {
  const { t } = useI18n(); const { data: d, error, isLoading, refetch } = useApi("/quality/impact");
  if (error) return <ErrorState error={error} retry={refetch} />; if (isLoading || !d) return <LoadingBlock />;
  const c = d.cost_of_poor_quality;
  const pareto = (d.pareto || []).map((x: any) => ({ ...x, label: t(x.defect_type) })); const causes = (d.causes || []).map((x: any) => ({ ...x, label: t(x.root_cause) }));
  return <Page title="Quality Control" sub="Where quality problems cost money." fresh={d.freshness}>
    <div className="grid gap-4 sm:grid-cols-3"><Stat label="QC loss" value={egp(c.qc_loss)} /><Stat label="Printing rework" value={egp(c.printing_rework)} /><Stat label="Quality-related refunds" value={egp(c.quality_refunds)} /></div>
    <div className="grid gap-4 xl:grid-cols-2"><Panel title="Top defects by loss"><ChartBox><BarChart data={pareto} layout="vertical"><CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" /><XAxis type="number" tick={axis} tickFormatter={(v) => axisK(v)} /><YAxis dataKey="label" type="category" width={140} tick={axis} /><Tooltip formatter={(v: any) => egp(v, false)} /><Bar dataKey="loss" name={t("Loss")} fill="var(--c-red)" radius={[0, 6, 6, 0]} /></BarChart></ChartBox></Panel>
      <Panel title="Root causes"><ChartBox><BarChart data={causes} layout="vertical"><CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" /><XAxis type="number" tick={axis} tickFormatter={(v) => axisK(v)} /><YAxis dataKey="label" type="category" width={150} tick={axis} /><Tooltip formatter={(v: any) => egp(v, false)} /><Bar dataKey="loss" name={t("Loss")} fill="var(--c-amber)" radius={[0, 6, 6, 0]} /></BarChart></ChartBox></Panel></div>
    <Panel title="Products affected" hint="Ranked by cost of poor quality (QC loss + quality-related refunds)"><div className="overflow-auto"><table className="w-full text-sm"><thead className="text-xs uppercase text-slate-500"><tr>{["Product", "Reject rate", "QC loss", "Quality refunds"].map((x) => <th key={x} className="py-2 text-start">{t(x)}</th>)}</tr></thead><tbody className="divide-y">{(d.products || []).slice(0, 10).map((p: any) => <tr key={p.product_id}><td className="py-2">{p.product_name}</td><td>{pct(p.reject_rate)}</td><td>{egp(p.loss)}</td><td>{egp(p.q_refund)}</td></tr>)}</tbody></table></div></Panel>
    <Panel title="Customer return impact"><div className="divide-y">{(d.returns || []).map((r: any) => <div key={r.return_reason} className="flex justify-between py-1.5 text-sm"><span>{r.return_reason}</span><span>{num(r.units)} {t("units")} · {egp(r.refund)}</span></div>)}</div></Panel>
    <Panel title="What the data does and does not show" hint={d.caution}><ul className="space-y-2 text-sm">{(d.findings || []).filter((f: any) => f.lag_months === 0).map((f: any, i: number) => <li key={i} className="flex items-start gap-2"><Badge kind={f.reliable ? "WARNING" : "LOW"}>{f.reliable ? t("Association") : t("No link found")}</Badge><span>{f.reading}</span></li>)}</ul></Panel></Page>;
}
