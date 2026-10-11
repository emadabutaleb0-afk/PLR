"use client";
import { ArrowRight } from "lucide-react";
import { useApi } from "@/lib/hooks";
import { egp, num, pct } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { Page, Panel } from "@/components/Page";
import { ErrorState, LoadingBlock, LoadingGrid } from "@/components/States";
import { Badge, Card } from "@/components/ui/primitives";

export default function Supply() {
  const { t, isAr } = useI18n(); const { data: d, error, isLoading, refetch } = useApi("/commercial/supply");
  if (error) return <ErrorState error={error} retry={refetch} />;
  if (isLoading || !d) return <><LoadingGrid n={5} /><div className="mt-6"><LoadingBlock /></div></>;
  const f = d.flow; const steps = [["Forecast demand (90d)", num(f.forecast_units), "units"], ["Stock on hand", num(f.stock_units), "units"], ["Production needed", num(f.production_need_units), "units"], ["Materials at risk", num(f.materials_at_risk), "materials"], ["Profit depending on supply", egp(f.profit_dependent), ""]];
  return <Page title="Supply Readiness" sub="Can the factory and the suppliers actually deliver what the forecast asks for?" fresh={d.freshness}>
    <div className="flex flex-wrap items-stretch gap-2">{steps.map(([l, v, u], i) => <div key={l} className="flex flex-1 items-center gap-2"><Card className="min-w-[150px] flex-1 p-4"><p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{t(l)}</p><p className="mt-1 text-xl font-semibold">{v} {u && <span className="text-sm font-normal text-slate-500">{t(u)}</span>}</p></Card>
      {i < steps.length - 1 && <ArrowRight className="hidden h-4 w-4 shrink-0 text-slate-300 xl:block rtl:rotate-180" />}</div>)}</div>
    <Panel title="Material requirements and supplier risk" hint="Requirement = production needed × bill of materials. Risk = lateness, delay and rejects over the last 12 months.">
      <div className="overflow-auto"><table className="w-full text-sm"><thead className="text-xs uppercase text-slate-500"><tr>{["Material", "Required (90d)", "Main supplier", "Late POs", "Delay when late", "Lead time (P90)", "Risk", "What to do"].map((x, i) => <th key={x} className={`whitespace-nowrap py-2 pe-3 ${i === 1 || i === 3 || i === 4 || i === 5 ? "text-end" : "text-start"}`}>{t(x)}</th>)}</tr></thead>
        <tbody className="divide-y divide-slate-100">{d.materials.map((m: any) => <tr key={m.material_id} className="align-top"><td className="py-2.5 pe-3 font-medium">{m.material_name}<div className="text-xs font-normal text-slate-400">{m.products} {t("products")}</div></td>
          <td className="pe-3 text-end">{num(m.requirement_gap_90d)} <span className="text-xs text-slate-400">{m.unit}</span></td><td className="pe-3 text-xs text-slate-600">{m.main_supplier || "—"}</td><td className="pe-3 text-end">{pct(m.late_rate, 0)}</td>
          <td className="pe-3 text-end">{num(m.avg_delay_when_late, 1)} {t("d")}</td><td className="pe-3 text-end">{num(m.lead_p90, 0)} {t("d")}</td><td className="pe-3"><Badge kind={m.risk}>{t(m.risk)} · {Math.round(m.risk_score)}</Badge></td><td className="max-w-xs text-xs text-slate-600">{m.action}</td></tr>)}</tbody></table></div></Panel>
    <Panel title="Can the replenishment be delivered?" hint="Products that need stock, checked against production bottlenecks, quality and material risk"><div className="divide-y divide-slate-100">{d.products.slice(0, 12).map((p: any) => <div key={p.product_id} className="grid gap-2 py-3 md:grid-cols-[1.2fr_2fr_auto] md:items-center">
      <div><p className="font-medium">{p.product_name}</p><p className="text-xs text-slate-400">{t("needs")} {num(p.need)} {t("units")}{p.so_high > 0 ? ` · ${p.so_high} ${t("high stockout risk")}` : ""}</p></div>
      <div className="text-sm text-slate-600"><p className="font-medium text-slate-700">{p.verdict}</p>{p.reasons?.length > 0 && <p className="text-xs">{p.reasons.join(isAr ? "، " : "; ")}</p>}</div>
      <div className="flex items-center gap-3 md:justify-end"><Badge kind={p.readiness}>{t(p.readiness)}</Badge><span className="w-24 text-end text-sm font-semibold">{egp(p.profit_dependent)}</span></div></div>)}</div></Panel>
    <Panel title="Limits" hint="What this view cannot tell you"><ul className="list-disc space-y-1.5 ps-5 text-sm text-slate-600">{d.limits.map((x: string, i: number) => <li key={i}>{x}</li>)}</ul></Panel>
  </Page>;
}
