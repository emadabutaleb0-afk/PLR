"use client";
import { useState } from "react";
import { createColumnHelper } from "@tanstack/react-table";
import { useApi } from "@/lib/hooks";
import { egp, pct, num } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { Page, Panel } from "@/components/Page";
import type { Query } from "@/components/DataTable";
import { DataTable, defaultQuery, qs } from "@/components/DataTable";
import { ErrorState, LoadingBlock } from "@/components/States";
import { Badge } from "@/components/ui/primitives";
const h = createColumnHelper<any>();
export default function Suppliers() {
  const { t } = useI18n(); const [q, setQ] = useState<Query>({ ...defaultQuery("rank"), order: "asc" }); const p = useApi(`/suppliers/performance?${qs(q)}`); const tc = useApi("/suppliers/true-cost");
  if (p.error) return <ErrorState error={p.error} retry={p.refetch} />;
  const cols = [h.accessor("rank", { header: "Rank" }), h.accessor("supplier_name", { header: "Supplier" }), h.accessor("on_time_rate", { header: "On-time", cell: (i) => pct(i.getValue(), 0) }), h.accessor("on_time_change_pp", { header: "Trend", cell: (i) => i.getValue() === null ? "—" : <span className={i.getValue() < -5 ? "text-rose-600" : "text-slate-500"}>{i.getValue() > 0 ? "+" : ""}{i.getValue().toFixed(0)} {t("pts")}</span> }),
    h.accessor("acceptance_rate", { header: "Acceptance", cell: (i) => pct(i.getValue()) }), h.accessor("avg_delay_days", { header: "Avg delay (days)", cell: (i) => num(i.getValue(), 1) }), h.accessor("spend", { header: "Purchase cost", cell: (i) => egp(i.getValue()) }),
    h.accessor("true_cost_score", { header: "True cost score", cell: (i) => <Badge kind={i.getValue() >= 60 ? "OK" : i.getValue() >= 35 ? "WARNING" : "CRITICAL"}>{i.getValue()}</Badge> }), h.accessor("affected_products", { header: "Products affected" })];
  const rows = tc.data?.table || [];
  return <Page title="Supplier Control" sub="True business cost, not just purchase price." fresh={p.data?.freshness}>
    <DataTable columns={cols} data={p.data?.items || []} total={p.data?.total || 0} pages={p.data?.pages || 1} query={q} setQuery={setQ} loading={p.isLoading} exportPath="/export/suppliers?format=csv" exportName="suppliers.csv" />
    {tc.isLoading ? <LoadingBlock /> : tc.data && <Panel title="Observed cost vs estimated risk cost" hint="Kept separate on purpose: observed = facts in the data; estimated = assumption-driven"><div className="overflow-auto"><table className="w-full text-sm"><thead className="text-xs uppercase text-slate-500"><tr>{["Supplier", "Observed cost", "Estimated risk cost", "True cost / spend"].map((x) => <th key={x} className="py-2 text-start">{t(x)}</th>)}</tr></thead><tbody className="divide-y">{[...rows].sort((a: any, b: any) => b.true_cost_index - a.true_cost_index).map((s: any) => <tr key={s.supplier_id}><td className="py-2">{s.supplier_name}</td><td>{egp(s.observed_cost)}</td><td className="text-amber-700">{egp(s.estimated_risk_cost)} <span className="text-xs">({t("estimate")})</span></td><td className="font-semibold">{pct(s.true_cost_index)}</td></tr>)}</tbody></table></div>
      <p className="mt-3 text-xs text-slate-500">{tc.data.labels?.observed}<br />{tc.data.labels?.estimated}</p>{tc.data.association && <p className="mt-2 text-xs text-slate-500">{t("Supplier delay vs production delay")}: {tc.data.association.reading} (rho {tc.data.association.rho}, {tc.data.association.months} {t("months")}).</p>}</Panel>}</Page>;
}
