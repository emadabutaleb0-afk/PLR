"use client";
import { useEffect, useState } from "react";
import { ArrowRight } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Legend, Tooltip, XAxis, YAxis } from "recharts";
import { useApi } from "@/lib/hooks";
import { egp, num, pct } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { Page, Panel, Stat } from "@/components/Page";
import { ChartBox, axis } from "@/components/Chart";
import { ErrorState, LoadingBlock, LoadingGrid } from "@/components/States";
import { Badge, Card, Input, Select } from "@/components/ui/primitives";

const CH_COLOR: Record<string, string> = { Retail: "var(--series-ink)", Online: "var(--series-gold)", Wholesale: "var(--c-muted)" };
export default function Allocation() {
  const { t } = useI18n(); const [only, setOnly] = useState(true); const { data: d, error, isLoading, refetch } = useApi(`/commercial/allocation?only_actionable=${only}`);
  const [pid, setPid] = useState(""); const [units, setUnits] = useState(500); const [u, setU] = useState(500);
  useEffect(() => { if (!pid && d?.rows?.length) setPid(d.rows[0].product_id); }, [d, pid]);
  useEffect(() => { const id = setTimeout(() => setU(Math.max(1, Math.min(1_000_000, Number(units) || 1))), 350); return () => clearTimeout(id); }, [units]);
  const sp = useApi(pid ? `/commercial/allocation/${pid}?units=${u}` : null);
  if (error) return <ErrorState error={error} retry={refetch} />;
  if (isLoading || !d) return <><LoadingGrid n={3} /><div className="mt-6"><LoadingBlock /></div></>;
  const s = d.summary || {}; const bc = (s.by_channel || []).map((x: any) => ({ ...x, label: t(x.channel) }));
  return <Page title="Channel Allocation" sub="How the stock we hold should be split across Retail, Online and Wholesale." fresh={d.freshness}>
    <div className="grid gap-4 sm:grid-cols-3"><Stat label="Products to rebalance" value={num(s.products_to_rebalance)} /><Stat label="Units to move" value={num(s.units_to_move)} /><Stat label="Extra profit (estimate)" value={egp(s.profit_uplift)} tone="text-emerald-600" /></div>
    <div className="grid gap-4 xl:grid-cols-2">
      <Panel title="Stock by channel: today vs recommended" hint="All products, units"><ChartBox h={260}><BarChart data={bc}><CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" /><XAxis dataKey="label" tick={axis} /><YAxis tick={axis} /><Tooltip /><Legend />
        <Bar dataKey="current" name={t("Today")} fill="var(--c-muted)" radius={[6, 6, 0, 0]} /><Bar dataKey="recommended" name={t("Recommended")} fill="var(--series-gold)" radius={[6, 6, 0, 0]} /></BarChart></ChartBox></Panel>
      <Panel title="Split a quantity" hint="Try a production batch or a delivery: how should it be divided?">
        <div className="flex flex-wrap items-end gap-3"><div className="min-w-[220px] flex-1"><label className="mb-1 block text-xs font-medium text-slate-600">{t("Product")}</label><Select className="w-full" value={pid} onChange={(e) => setPid(e.target.value)}>{d.rows.map((r: any) => <option key={r.product_id} value={r.product_id}>{r.product_name}</option>)}</Select></div>
          <div className="w-32"><label className="mb-1 block text-xs font-medium text-slate-600">{t("Units")}</label><Input type="number" min={1} value={units} onChange={(e) => setUnits(Number(e.target.value))} /></div></div>
        {sp.isLoading ? <div className="mt-4"><LoadingBlock h="h-28" /></div> : sp.data && <div className="mt-4 space-y-3">
          <div className="flex h-4 overflow-hidden rounded-full bg-slate-100">{sp.data.split.map((x: any) => <div key={x.channel} style={{ width: `${x.share * 100}%`, background: CH_COLOR[x.channel] || "var(--c-muted)" }} />)}</div>
          <div className="grid gap-3 sm:grid-cols-3">{sp.data.split.map((x: any) => <div key={x.channel} className="rounded-xl border border-slate-100 p-3"><p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500"><span className="h-2.5 w-2.5 rounded-full" style={{ background: CH_COLOR[x.channel] || "var(--c-muted)" }} />{t(x.channel)}</p>
            <p className="mt-1 text-2xl font-semibold">{num(x.units)}</p><p className="text-xs text-slate-400">{pct(x.share, 0)} · {t("demand")} {num(x.demand)} · {egp(x.gp_unit, false)}/{t("unit")}</p></div>)}</div></div>}</Panel></div>
    <Card className="overflow-hidden"><div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-4"><div><h3 className="font-semibold">{t("Allocation by product")}</h3><p className="text-xs text-slate-500">{t("Sorted by extra profit. Current → recommended units per channel.")}</p></div>
      <label className="flex items-center gap-2 text-sm text-slate-600"><input type="checkbox" checked={only} onChange={(e) => setOnly(e.target.checked)} />{t("Only products worth acting on")}</label></div>
      <div className="max-h-[560px] overflow-auto"><table className="sticky-th w-full text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-3 py-2.5 text-start">{t("Product")}</th><th className="px-3 text-end">{t("Units held")}</th>
        {["Retail", "Online", "Wholesale"].map((c) => <th key={c} className="px-3 text-start">{t(c)}</th>)}<th className="px-3 text-end">{t("Extra profit (estimate)")}</th></tr></thead>
        <tbody className="divide-y divide-slate-100">{d.rows.slice(0, 60).map((r: any) => <tr key={r.product_id} className="hover:bg-slate-50/70"><td className="px-3 py-2.5 font-medium">{r.product_name}{r.short_channels?.length > 0 && <div className="mt-1 flex flex-wrap gap-1">{r.short_channels.map((c: string) => <Badge key={c} kind="WARNING">{t("short")}: {t(c)}</Badge>)}</div>}</td><td className="px-3 text-end">{num(r.pool_units)}</td>
          {["Retail", "Online", "Wholesale"].map((c) => { const x = r.channels.find((y: any) => y.channel === c); return <td key={c} className="whitespace-nowrap px-3">{x ? <span className="inline-flex items-center gap-1.5"><span className="text-slate-400">{num(x.current)}</span><ArrowRight className="h-3 w-3 text-slate-300 rtl:rotate-180" /><b className={x.shift > 0 ? "text-emerald-600" : x.shift < 0 ? "text-rose-600" : ""}>{num(x.recommended)}</b></span> : "—"}</td>; })}
          <td className="px-3 text-end font-semibold text-emerald-600">{egp(r.profit_uplift)}</td></tr>)}</tbody></table></div></Card>
    <p className="text-xs text-slate-500">{s.label} {d.note}</p>
  </Page>;
}
