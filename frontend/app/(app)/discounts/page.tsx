"use client";
import { Bar, BarChart, CartesianGrid, Cell, Tooltip, XAxis, YAxis } from "recharts";
import { Lightbulb } from "lucide-react";
import { useApi } from "@/lib/hooks";
import { egp, num, pct } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { Page, Panel, Stat } from "@/components/Page";
import { ChartBox, axis } from "@/components/Chart";
import { ErrorState, LoadingBlock, LoadingGrid } from "@/components/States";
import { Badge, Card } from "@/components/ui/primitives";

export default function Discounts() {
  const { t } = useI18n(); const { data: d, error, isLoading, refetch } = useApi("/commercial/discounts");
  if (error) return <ErrorState error={error} retry={refetch} />;
  if (isLoading || !d) return <><LoadingGrid n={3} /><div className="mt-6"><LoadingBlock /></div></>;
  return <Page title="Discount Intelligence" sub="What discounting has really done to volume and profit." fresh={d.freshness}>
    <Card className="flex gap-3 border-brand-200 bg-brand-50 p-5"><Lightbulb className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" /><div><p className="font-semibold text-brand-700">{t("What the data says")}</p><p className="mt-1 text-slate-700">{d.headline}</p></div></Card>
    <div className="grid gap-4 sm:grid-cols-3"><Stat label="Discount given above the comfort band" value={egp(d.excess_total)} tone="text-rose-600" /><Stat label="Comfort band" value={pct(d.comfort, 0)} /><Stat label="Products with heavy discounting" value={num(d.products_above_cap)} /></div>
    {d.channels.map((ch: any) => <Panel key={ch.channel} title={ch.channel} hint={`${t("Average discount")} ${pct(ch.avg_discount, 1)} · ${num(ch.units)} ${t("units")} · ${t(d.window_label)}`}>
      <div className="grid gap-5 xl:grid-cols-2"><div><p className="mb-2 text-xs font-medium text-slate-500">{t("Gross profit per unit by discount band")}</p>
        <ChartBox h={220}><BarChart data={ch.bands}><CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" /><XAxis dataKey="band" tick={axis} /><YAxis tick={axis} /><Tooltip formatter={(v: any) => egp(v, false)} /><Bar dataKey="gp_unit" name={t("Gross profit per unit")} radius={[6, 6, 0, 0]}>{ch.bands.map((_: any, i: number) => <Cell key={i} fill={i === 0 ? "var(--series-ink)" : "var(--series-gold)"} />)}</Bar></BarChart></ChartBox></div>
        <div className="overflow-auto"><table className="w-full text-sm"><thead className="text-xs uppercase text-slate-500"><tr><th className="py-2 text-start">{t("Band")}</th><th className="text-end">{t("Units / line")}</th><th className="text-end">{t("Margin")}</th><th className="text-end">{t("Break-even lift")}</th></tr></thead>
          <tbody className="divide-y divide-slate-100">{ch.bands.map((b: any, i: number) => <tr key={b.band}><td className="py-2 font-medium">{b.band}</td><td className="text-end">{num(b.units_per_line, 2)}</td><td className="text-end">{pct(b.margin, 1)}</td><td className="text-end font-semibold">{i === 0 || b.breakeven_lift === null ? "—" : `+${pct(b.breakeven_lift, 0)}`}</td></tr>)}</tbody></table>
          <p className="mt-2 text-xs text-slate-500">{t("Break-even lift = extra units needed to earn the same gross profit as the shallowest band.")}</p></div></div>
      <div className="mt-4 rounded-xl bg-slate-50 p-4 text-sm"><p className="font-medium">{t("Does a deeper discount sell more?")}</p><p className="mt-1 text-slate-600">{ch.test.verdict}</p>
        {ch.test.coef !== null && ch.test.coef !== undefined && <p className="mt-1 text-xs text-slate-500">{t("Measured change in units per +5 points of discount")}: <b>{pct(ch.test.per5pp, 1)}</b> ({pct(ch.test.per5pp_low, 1)} {t("to")} {pct(ch.test.per5pp_high, 1)}, {t("95% range")}) · {num(ch.test.n)} {t("product-months")}</p>}</div></Panel>)}
    <Panel title="Products with the most discount given away" hint="Retail and Online, last 12 months. Cap = lower of the comfort band and the deepest discount that keeps the margin floor."><div className="overflow-auto"><table className="w-full text-sm"><thead className="text-xs uppercase text-slate-500"><tr>
      {["Product", "Average discount", "Units sold deep", "Margin", "Given away above band", "Recommended cap"].map((x, i) => <th key={x} className={`py-2 ${i === 0 ? "text-start" : "text-end"}`}>{t(x)}</th>)}</tr></thead>
      <tbody className="divide-y divide-slate-100">{d.products.slice(0, 15).map((p: any) => <tr key={p.product_id}><td className="py-2 pe-3 font-medium">{p.product_name}{p.above_cap && <Badge kind="WARNING" className="ms-2">{t("heavy")}</Badge>}</td><td className="text-end">{pct(p.avg_discount, 1)}</td><td className="text-end">{pct(p.deep_share, 0)}</td><td className="text-end">{pct(p.margin, 1)}</td>
        <td className="text-end font-semibold text-rose-600">{egp(p.excess)}</td><td className="text-end font-semibold">{pct(p.recommended_cap, 0)}</td></tr>)}</tbody></table></div></Panel>
    <Panel title="How to read this" hint="Limits of the analysis"><ul className="list-disc space-y-1.5 ps-5 text-sm text-slate-600">{d.caveats.map((c: string, i: number) => <li key={i}>{c}</li>)}</ul></Panel>
  </Page>;
}
