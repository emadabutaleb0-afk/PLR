"use client";
import { useState } from "react";
import { createColumnHelper } from "@tanstack/react-table";
import { useApi } from "@/lib/hooks";
import { DEAD_TEXT, RISK_TEXT, egp, num } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { Page, Panel, Stat } from "@/components/Page";
import { DataTable, defaultQuery, qs } from "@/components/DataTable";
import { ErrorState, LoadingBlock } from "@/components/States";
import { Badge, Card } from "@/components/ui/primitives";
const h = createColumnHelper<any>();
const heat = (d: number) => d < 7 ? "bg-rose-400" : d < 21 ? "bg-amber-300" : d < 90 ? "bg-emerald-300" : d < 180 ? "bg-sky-300" : "bg-violet-400";
export default function Inventory() {
  const { t } = useI18n(); const [tab, setTab] = useState("risk"); const hl = useApi("/inventory/health"); const [q, setQ] = useState(defaultQuery("estimated_value_egp")); const [q2, setQ2] = useState(defaultQuery("stock_value_at_risk")); const [q3, setQ3] = useState(defaultQuery("revenue_protected"));
  const so = useApi(tab === "risk" ? `/inventory/stockout-risk?${qs(q)}` : null); const dd = useApi(tab === "dead" ? `/inventory/dead-stock?${qs(q2)}` : null); const tr = useApi(tab === "transfers" ? `/inventory/transfers?${qs(q3)}` : null); const ls = useApi(tab === "lost" ? "/inventory/lost-sales" : null);
  if (hl.error) return <ErrorState error={hl.error} retry={hl.refetch} />;
  const prods = hl.data ? Array.from(new Set(hl.data.heatmap.map((x: any) => x.product_name))) as string[] : []; const locs = hl.data?.locations || [];
  const cSo = [h.accessor("product_name", { header: "Product" }), h.accessor("location_name", { header: "Location" }), h.accessor("closing_stock", { header: "Stock", cell: (i) => num(i.getValue()) }), h.accessor("doc", { header: "Days of cover", cell: (i) => num(i.getValue(), 1) }),
    h.accessor("stockout_risk", { header: "Risk", cell: (i) => <Badge kind={i.getValue()}>{t(RISK_TEXT[i.getValue()] || i.getValue())}</Badge> }), h.accessor("estimated_value_egp", { header: "Value at stake", cell: (i) => egp(i.getValue()) })];
  const cDd = [h.accessor("product_name", { header: "Product" }), h.accessor("location_name", { header: "Location" }), h.accessor("doc", { header: "Days of cover", cell: (i) => num(i.getValue(), 0) }), h.accessor("excess_units", { header: "Excess units", cell: (i) => num(i.getValue()) }),
    ...(dd.data?.items?.[0] && "stock_value_at_risk" in dd.data.items[0] ? [h.accessor("stock_value_at_risk", { header: "Value at risk", cell: (i) => egp(i.getValue()) })] : []),
    h.accessor("dead_risk", { header: "Risk", cell: (i) => <Badge kind={i.getValue()}>{t(DEAD_TEXT[i.getValue()] || i.getValue())}</Badge> }), h.accessor("primary_action", { header: "Rescue", cell: (i) => i.getValue() ? t(String(i.getValue()).replace(/_/g, " ")) : "—" }),
    h.accessor("md_discount", { header: "Discount", cell: (i) => i.getValue() ? `${Math.round(i.getValue() * 100)}%` : "—" })];
  const cTr = [h.accessor("product_name", { header: "Product" }), h.accessor("from_name", { header: "From" }), h.accessor("to_name", { header: "To" }), h.accessor("units", { header: "Units", cell: (i) => <b>{num(i.getValue())}</b> }),
    h.accessor("from_cover_days", { header: "Cover at source", cell: (i) => `${num(i.getValue(), 0)} ${t("d")}` }), h.accessor("to_cover_days", { header: "Cover at destination", cell: (i) => `${num(i.getValue(), 1)} ${t("d")}` }),
    h.accessor("revenue_protected", { header: "Revenue protected", cell: (i) => <span className="text-emerald-600">{egp(i.getValue())}</span> })];
  const TABS: [string, string][] = [["risk", "Stockout risk"], ["dead", "Dead & excess stock"], ["transfers", "Transfer opportunities"], ["lost", "Lost sales"]];
  return <Page title="Inventory Control" sub="Where stock is short, where it is trapped, and what to move." fresh={hl.data?.freshness}>
    {hl.isLoading || !hl.data ? <LoadingBlock /> : <><div className="grid gap-4 md:grid-cols-3">{locs.map((l: any) => <Card key={l.location_id} className="p-5"><h3 className="font-semibold">{l.location_name}</h3><p className="text-2xl font-semibold">{num(l.stock_units)} <span className="text-sm font-normal text-slate-500">{t("units")}</span></p><p className="text-sm text-slate-500">{t("Median cover")} {num(l.median_cover_days, 0)} {t("days")}</p><div className="mt-2 flex flex-wrap gap-1.5"><Badge kind="CRITICAL">{l.stockout_high} {t("high stockout risk")}</Badge><Badge kind="WARNING">{l.stockout_medium} {t("watch")}</Badge><Badge kind="INFO">{l.dead_high + l.dead_medium} {t("slow/dead")}</Badge></div></Card>)}</div>
      <Panel title="Days-of-cover heatmap" hint="Red = short on stock · green = healthy · violet = excess"><div className="overflow-auto"><table className="text-xs"><thead><tr><th className="p-1 text-start">{t("Product")}</th>{locs.map((l: any) => <th key={l.location_id} className="p-1">{l.location_name}</th>)}</tr></thead><tbody>{prods.slice(0, 60).map((p) => <tr key={p}><td className="whitespace-nowrap p-1 pe-3">{p}</td>{locs.map((l: any) => { const c = hl.data.heatmap.find((x: any) => x.product_name === p && x.location_id === l.location_id); return <td key={l.location_id} className="p-0.5">{c ? <div title={`${num(c.days_of_cover, 0)} ${t("days")}`} className={`h-6 min-w-[70px] rounded text-center leading-6 ${heat(c.days_of_cover)}`}>{num(c.days_of_cover, 0)}</div> : null}</td>; })}</tr>)}</tbody></table></div></Panel></>}
    <div className="flex flex-wrap gap-1 border-b border-slate-200">{TABS.map(([k, l]) => <button key={k} onClick={() => setTab(k)} className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${tab === k ? "border-brand-600 text-brand-700" : "border-transparent text-slate-500"}`}>{t(l)}</button>)}</div>
    {tab === "risk" && <DataTable columns={cSo} data={so.data?.items || []} total={so.data?.total || 0} pages={so.data?.pages || 1} query={q} setQuery={setQ} loading={so.isLoading} />}
    {tab === "dead" && <DataTable columns={cDd} data={dd.data?.items || []} total={dd.data?.total || 0} pages={dd.data?.pages || 1} query={q2} setQuery={setQ2} loading={dd.isLoading} exportPath="/export/dead-stock?format=csv" exportName="dead-stock.csv" />}
    {tab === "transfers" && <><DataTable columns={cTr} data={tr.data?.items || []} total={tr.data?.total || 0} pages={tr.data?.pages || 1} query={q3} setQuery={setQ3} loading={tr.isLoading} />{tr.data?.note && <p className="text-xs text-slate-500">{tr.data.note}</p>}</>}
    {tab === "lost" && (ls.isLoading ? <LoadingBlock /> : ls.error ? <ErrorState error={ls.error} retry={ls.refetch} /> : ls.data && <div className="space-y-4"><div className="grid gap-4 sm:grid-cols-3"><Stat label="Lost revenue (12m, estimate)" value={egp(ls.data.summary.lost_revenue_12m)} tone="text-rose-600" /><Stat label="Lost units (12m)" value={num(ls.data.summary.lost_units_12m)} /><Stat label="Lost revenue (3m)" value={egp(ls.data.summary.lost_revenue_3m)} /></div><p className="text-xs text-slate-500">{ls.data.summary.label}</p></div>)}
  </Page>;
}
