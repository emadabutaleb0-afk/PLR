"use client";
import Link from "next/link";
import { Bar, BarChart, CartesianGrid, Legend, Tooltip, XAxis, YAxis } from "recharts";
import { useApi } from "@/lib/hooks";
import { axisM, egp, pct } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { Page, Panel, Stat } from "@/components/Page";
import { ChartBox, axis } from "@/components/Chart";
import { ErrorState, LoadingBlock, LoadingGrid } from "@/components/States";
import { Badge, Card } from "@/components/ui/primitives";
import { LEAK_COLOR, LEAK_KEYS, LEAK_LABEL } from "@/components/leak";

export default function Leakage() {
  const { t } = useI18n(); const { data: d, error, isLoading, refetch } = useApi("/commercial/leakage");
  if (error) return <ErrorState error={error} retry={refetch} />;
  if (isLoading || !d) return <><LoadingGrid n={4} /><div className="mt-6"><LoadingBlock /></div></>;
  const r = d.reconciliation; const par = d.profit_at_risk;
  return <Page title="Profit Leakage" sub="Where the business loses money, in one additive view." fresh={d.freshness}>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Stat label="Total leakage (12 months)" value={egp(d.total)} tone="text-rose-600" />
      <Stat label="Largest source" value={d.items[0] ? `${d.items[0].label}` : "—"} />
      <Stat label="Profit at risk (next period)" value={egp(par.total)} tone="text-amber-600" />
      <Stat label="Period" value={<span className="text-lg">{t(d.window_label)}</span>} /></div>
    <Card className="p-5"><div className="flex h-4 overflow-hidden rounded-full bg-slate-100">{d.items.map((i: any) => <div key={i.key} title={`${i.label} ${pct(i.share, 1)}`} style={{ width: `${(i.share || 0) * 100}%`, background: LEAK_COLOR[i.key] }} />)}</div>
      <div className="mt-5 divide-y divide-slate-100">{d.items.map((i: any) => <div key={i.key} className="grid gap-2 py-3 md:grid-cols-[1fr_auto] md:items-center">
        <div><div className="flex flex-wrap items-center gap-2"><span className="h-3 w-3 rounded-full" style={{ background: LEAK_COLOR[i.key] }} /><span className="font-semibold">{i.label}</span><Badge kind={i.basis}>{t(i.basis)}</Badge><Link href={i.page} className="text-xs font-medium text-brand-700 hover:underline">{t("Open")}</Link></div>
          <p className="mt-1 max-w-3xl text-xs text-slate-500">{i.definition}</p></div>
        <div className="text-end"><p className="text-lg font-semibold">{egp(i.value)}</p><p className="text-xs text-slate-400">{pct(i.share, 1)} {t("of total")}</p></div></div>)}</div></Card>
    <div className="grid gap-4 xl:grid-cols-2">
      <Panel title="Leakage by month" hint="Stacked by type, last 12 months"><ChartBox h={300}><BarChart data={d.by_month}><CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" /><XAxis dataKey="month" tick={axis} /><YAxis tick={axis} tickFormatter={(v) => axisM(v, 1)} /><Tooltip formatter={(v: any) => egp(v, false)} /><Legend />
        {LEAK_KEYS.map((k) => <Bar key={k} dataKey={k} name={t(LEAK_LABEL[k])} stackId="a" fill={LEAK_COLOR[k]} />)}</BarChart></ChartBox></Panel>
      <Panel title="Where to start: top products" hint="Largest leakage over 12 months and the main driver"><div className="overflow-auto"><table className="w-full text-sm"><thead className="text-xs uppercase text-slate-500"><tr><th className="py-2 text-start">{t("Product")}</th><th className="text-start">{t("Main driver")}</th><th className="text-end">{t("Leakage")}</th></tr></thead>
        <tbody className="divide-y divide-slate-100">{d.top_products.slice(0, 10).map((p: any) => <tr key={p.product_id}><td className="py-2 pe-3"><Link href={`/products/${p.product_id}`} className="font-medium hover:underline">{p.product_name}</Link></td>
          <td><span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full" style={{ background: LEAK_COLOR[p.main_driver] }} />{t(LEAK_LABEL[p.main_driver])}</span></td><td className="text-end font-semibold">{egp(p.total)}</td></tr>)}</tbody></table></div></Panel></div>
    <Panel title="Read this before you quote the numbers" hint="Basis, limits and reconciliation"><ul className="list-disc space-y-1.5 ps-5 text-sm text-slate-600">{d.notes.map((n: string, i: number) => <li key={i}>{n}</li>)}
      <li>{par.label}</li></ul>
      {r && <div className="mt-4 rounded-xl bg-slate-50 p-4 text-sm"><p className="font-medium">{t("Volume reconciliation")}</p><p className="mt-1 text-slate-600">{r.label}</p>
        <div className="mt-2 grid gap-2 text-xs text-slate-500 sm:grid-cols-4"><span>{t("Units sold")}: <b className="text-slate-700">{Math.round(r.units_sold).toLocaleString("en-US")}</b></span><span>{t("Units produced")}: <b className="text-slate-700">{Math.round(r.units_produced).toLocaleString("en-US")}</b></span>
          <span>{t("Attribution ratio")}: <b className="text-slate-700">{r.attribution_ratio === null ? "—" : pct(r.attribution_ratio, 0)}</b></span><span>{t("Unscaled factory leakage")}: <b className="text-slate-700">{egp((r.unscaled_quality || 0) + (r.unscaled_production || 0))}</b></span></div></div>}</Panel>
  </Page>;
}
