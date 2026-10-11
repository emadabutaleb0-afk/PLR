"use client";
import { useState } from "react";
import { createColumnHelper } from "@tanstack/react-table";
import { Bar, BarChart, CartesianGrid, Legend, Tooltip, XAxis, YAxis } from "recharts";
import { useApi } from "@/lib/hooks";
import { egp, num, axisM } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { Page, Panel, Stat } from "@/components/Page";
import { ChartBox, axis } from "@/components/Chart";
import { DataTable, defaultQuery, qs } from "@/components/DataTable";
import { ErrorState, LoadingBlock } from "@/components/States";
import { Badge } from "@/components/ui/primitives";
const h = createColumnHelper<any>();
export default function Marketing() {
  const { t } = useI18n(); const p = useApi("/marketing/performance"); const [q, setQ] = useState(defaultQuery("estimated_impact_egp")); const c = useApi(`/marketing/collisions?${qs(q)}`);
  if (p.error) return <ErrorState error={p.error} retry={p.refetch} />; if (p.isLoading || !p.data) return <LoadingBlock />;
  const prod = p.data.by_product || []; const over = prod.filter((x: any) => x.support === "TOO_MUCH_SPEND").sort((a: any, b: any) => b.support_ratio - a.support_ratio).slice(0, 6); const under = prod.filter((x: any) => x.support === "TOO_LITTLE_SUPPORT").sort((a: any, b: any) => a.support_ratio - b.support_ratio).slice(0, 6);
  const cols = [h.accessor("severity", { header: "Severity", cell: (i) => <Badge kind={i.getValue()}>{t(i.getValue())}</Badge> }), h.accessor("type", { header: "Collision", cell: (i) => t(String(i.getValue()).replace(/_/g, " ")) }), h.accessor("campaign_name", { header: "Campaign" }), h.accessor("product_id", { header: "Product" }),
    h.accessor("why", { header: "Why", cell: (i) => <span className="text-slate-600">{i.getValue()}</span> }), h.accessor("estimated_impact_egp", { header: "Impact (est.)", cell: (i) => egp(i.getValue()) }), h.accessor("recommended_marketing_action", { header: "Do this" })];
  const ratio = (x: any) => `${num(x.support_ratio, 1)}x ${t("its profit share")}`;
  return <Page title="Marketing Control" sub="Is spend going where stock and quality can support it?" fresh={p.data.freshness}>
    <div className="grid gap-4 sm:grid-cols-3"><Stat label="Spend (all time)" value={egp(p.data.summary.spend)} /><Stat label="Attributed revenue" value={egp(p.data.summary.revenue)} /><Stat label="ROAS" value={`${p.data.summary.roas}x`} /></div>
    <p className="text-xs text-slate-500">{p.data.summary.label}</p>
    <div className="grid gap-4 xl:grid-cols-2"><Panel title="Spend vs revenue by platform"><ChartBox h={240}><BarChart data={p.data.by_platform}><CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" /><XAxis dataKey="platform" tick={axis} /><YAxis tick={axis} tickFormatter={(v) => axisM(v, 1)} /><Tooltip formatter={(v: any) => egp(v, false)} /><Legend /><Bar dataKey="spend" name={t("Spend")} fill="var(--c-amber)" /><Bar dataKey="revenue" name={t("Revenue")} fill="var(--series-ink)" /></BarChart></ChartBox></Panel>
      <div className="grid gap-4"><Panel title="Receiving too much spend" hint="Spend share far above profit share">{over.length ? over.map((x: any) => <div key={x.product_id} className="flex justify-between gap-3 py-1 text-sm"><span>{x.product_name}</span><span className="text-slate-500">{ratio(x)}</span></div>) : <p className="text-sm text-slate-400">{t("Nothing to show.")}</p>}</Panel>
        <Panel title="Receiving too little support" hint="Profit share far above spend share">{under.length ? under.map((x: any) => <div key={x.product_id} className="flex justify-between gap-3 py-1 text-sm"><span>{x.product_name}</span><span className="text-slate-500">{ratio(x)}</span></div>) : <p className="text-sm text-slate-400">{t("Nothing to show.")}</p>}</Panel></div></div>
    <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">{t("Campaign ↔ inventory collisions")}</h2>
    <DataTable columns={cols} data={c.data?.items || []} total={c.data?.total || 0} pages={c.data?.pages || 1} query={q} setQuery={setQ} loading={c.isLoading} empty="No collisions detected." /></Page>;
}
