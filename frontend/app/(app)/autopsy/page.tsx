"use client";
import { Bar, BarChart, CartesianGrid, Cell, Tooltip, XAxis, YAxis } from "recharts";
import { useApi } from "@/lib/hooks";
import { axisM, egp, pct } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { Page, Panel, Stat } from "@/components/Page";
import { ChartBox, axis } from "@/components/Chart";
import { ErrorState, LoadingBlock, LoadingGrid } from "@/components/States";
import { Badge, Card } from "@/components/ui/primitives";

const LEVEL_KIND: Record<string, string> = { accounting: "OK", observed: "INFO", estimate: "ESTIMATE", association: "WATCH", hypothesis: "LOW" };

export default function Autopsy() {
  const { t } = useI18n(); const { data: d, error, isLoading, refetch } = useApi("/commercial/autopsy");
  if (error) return <ErrorState error={error} retry={refetch} />;
  if (isLoading || !d) return <><LoadingGrid n={4} /><div className="mt-6"><LoadingBlock /></div></>;
  const rows = (d.drivers || []).map((x: any) => ({ ...x, name: ((s: string) => s.charAt(0).toUpperCase() + s.slice(1))(t(x.label)) }));
  return <Page title="Business Autopsy" sub="Why contribution moved, and what other departments' data says about the same place." fresh={d.freshness}>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Stat label="Change in contribution" value={egp(d.delta_egp)} tone={d.delta_egp < 0 ? "text-rose-600" : "text-emerald-600"} />
      <Stat label="Now" value={egp(d.contribution_now_egp)} /><Stat label="Previous period" value={egp(d.contribution_prev_egp)} />
      <Stat label="Adds up exactly" value={d.reconciles ? t("Yes") : t("No")} tone={d.reconciles ? "text-emerald-600" : "text-rose-600"} /></div>
    {(d.warnings || []).map((w: any) => <Card key={w.code} className="border-amber-200 bg-amber-50 p-4 text-sm text-amber-900" role="note">{w.text}</Card>)}
    <Panel title="What moved the number" hint={d.window_label}>
      <ChartBox h={320}><BarChart data={rows} layout="vertical" margin={{ left: 20 }}><CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" /><XAxis type="number" tick={axis} tickFormatter={(v) => axisM(v, 1)} />
        <YAxis type="category" dataKey="name" width={150} tick={axis} /><Tooltip formatter={(v: any) => egp(v, false)} />
        <Bar dataKey="effect_egp" name={t("Effect on contribution")}>{rows.map((r: any) => <Cell key={r.key} fill={r.effect_egp < 0 ? "var(--c-red)" : "var(--c-green)"} />)}</Bar></BarChart></ChartBox></Panel>
    <div className="space-y-4"><h2 className="text-lg font-semibold">{t("Evidence chains for the biggest drags")}</h2>
      {(d.chains || []).length === 0 && <Card className="p-4 text-sm text-slate-500">{t("No driver is dragging contribution down in this period.")}</Card>}
      {(d.chains || []).map((c: any) => <Card key={c.driver} className="p-5"><div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-semibold first-letter:uppercase">{t(c.label)}</h3><span className="font-semibold text-rose-600">{egp(c.effect_egp)}</span></div>
        <ol className="mt-3 space-y-3 border-s border-slate-200 ps-4">{c.links.map((l: any, i: number) => <li key={i}><div className="flex flex-wrap items-center gap-2"><Badge kind={LEVEL_KIND[l.level]}>{t(l.level)}</Badge><span className="text-xs text-slate-400">{l.stage} · {l.source}</span></div>
          <p className="mt-1 text-sm text-slate-700">{l.statement}</p>{l.caveat && <p className="text-xs text-slate-400">{l.caveat}</p>}</li>)}</ol>
        <p className="mt-3 text-xs text-slate-400">{t("Cause: not established. These links show where to look, not who is to blame.")}</p></Card>)}</div>
    <div className="grid gap-4 xl:grid-cols-2">
      <Panel title="By product family" hint="Change in contribution and the main drag">
        <table className="w-full text-sm"><thead className="text-xs uppercase text-slate-500"><tr><th className="py-2 text-start">{t("Family")}</th><th className="text-end">{t("Change")}</th><th className="text-start ps-3">{t("Main drag")}</th></tr></thead>
          <tbody className="divide-y divide-slate-100">{(d.by_family || []).map((f: any) => <tr key={f.family}><td className="py-2 font-medium">{f.family}</td><td className="text-end">{egp(f.delta_egp)}</td><td className="ps-3 text-slate-500">{f.main_drag_label ? `${t(f.main_drag_label)} (${egp(f.main_drag_egp)})` : "—"}</td></tr>)}</tbody></table></Panel>
      <Panel title="Products that lost the most" hint="Biggest fall in contribution">
        <table className="w-full text-sm"><thead className="text-xs uppercase text-slate-500"><tr><th className="py-2 text-start">{t("Product")}</th><th className="text-end">{t("Change")}</th><th className="text-end">{t("Margin")}</th><th className="text-start ps-3">{t("Main drag")}</th></tr></thead>
          <tbody className="divide-y divide-slate-100">{(d.worst_products || []).map((p: any) => <tr key={p.product_id}><td className="py-2 font-medium">{p.product_name}</td><td className="text-end">{egp(p.delta_egp)}</td><td className="text-end">{pct(p.margin_prev, 0)} → {pct(p.margin, 0)}</td><td className="ps-3 text-slate-500">{p.main_drag_label ? t(p.main_drag_label) : "—"}</td></tr>)}</tbody></table></Panel></div>
    <Panel title="How to read the evidence labels" hint="Every link in a chain carries one"><div className="grid gap-2 text-sm sm:grid-cols-2">{Object.entries(d.legend || {}).map(([k, v]) => <p key={k}><Badge kind={LEVEL_KIND[k]}>{t(k)}</Badge> <span className="ms-2 text-slate-600">{String(v)}</span></p>)}</div>
      <ul className="mt-4 list-disc space-y-1.5 ps-5 text-sm text-slate-600">{(d.notes || []).map((n: string, i: number) => <li key={i}>{n}</li>)}</ul></Panel>
  </Page>;
}
