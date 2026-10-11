"use client";
import { useApi } from "@/lib/hooks";
import { ACTION_LABEL, egp, num, pct } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { Page, Panel } from "@/components/Page";
import { ErrorState, LoadingBlock } from "@/components/States";
import { Badge } from "@/components/ui/primitives";
export default function Merch() {
  const { t } = useI18n(); const { data, error, isLoading, refetch } = useApi("/merchandising/overview");
  if (error) return <ErrorState error={error} retry={refetch} />; if (isLoading || !data) return <LoadingBlock />;
  const List = ({ rows, right }: { rows: any[]; right: (r: any) => React.ReactNode }) => rows?.length ? <div className="divide-y divide-slate-100">{rows.map((r, i) => <div key={i} className="flex items-center justify-between gap-3 py-2 text-sm"><span>{r.product_name}{r.location_name && <span className="ms-1 text-xs text-slate-400">· {r.location_name}</span>}</span><span className="text-end">{right(r)}</span></div>)}</div> : <p className="text-sm text-slate-400">{t("Nothing to show.")}</p>;
  const v = (r: any) => <span className="font-semibold text-emerald-600">{egp(r.estimated_value_egp)}</span>;
  return <Page title="Merchandising" sub="What to scale, discount and move." fresh={data.freshness}><div className="grid gap-4 xl:grid-cols-2">
    <Panel title="Top sellers (last 90 days)"><List rows={data.top_sellers} right={(r) => `${num(r.units_90d)} ${t("units")}`} /></Panel>
    {data.high_margin_winners?.[0] && "margin" in data.high_margin_winners[0] && <Panel title="High-margin winners"><List rows={data.high_margin_winners} right={(r) => `${pct(r.margin)} ${t("margin")}`} /></Panel>}
    <Panel title="Products to scale"><List rows={data.to_scale} right={v} /></Panel><Panel title="Products to discount"><List rows={data.to_discount} right={v} /></Panel>
    <Panel title="Products to relocate"><List rows={data.to_relocate} right={v} /></Panel>
    <Panel title="Dead stock"><List rows={data.dead_stock} right={(r) => <Badge kind={r.dead_risk}>{num(r.doc, 0)} {t("days of cover")}</Badge>} /></Panel>
    <Panel title="Size imbalance" hint="Sizes whose demand mix moved most vs the prior 12 months"><List rows={data.size_imbalance} right={(r) => `${r.share_shift_pp?.toFixed(1)} ${t("pts shift")}`} /></Panel>
    <Panel title="Product strategy mix">{Object.entries(data.decision_mix || {}).map(([k, n]: any) => <div key={k} className="flex justify-between py-1 text-sm"><span>{t(ACTION_LABEL[k] || k)}</span><b>{n}</b></div>)}</Panel></div></Page>;
}
