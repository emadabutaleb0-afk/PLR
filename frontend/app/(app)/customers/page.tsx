"use client";
import { useApi } from "@/lib/hooks";
import { egp, num, pct } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { Page, Panel, Stat } from "@/components/Page";
import { ErrorState, LoadingBlock, LoadingGrid } from "@/components/States";
import { Badge, Card } from "@/components/ui/primitives";

const SEG: Record<string, string> = { Active: "var(--c-green)", Slipping: "var(--c-amber)", Lapsed: "var(--c-red)", New: "var(--c-sky)", "One-time": "var(--c-muted)" };
export default function Customers() {
  const { t } = useI18n(); const { data: d, error, isLoading, refetch } = useApi("/commercial/customers");
  if (error) return <ErrorState error={error} retry={refetch} />;
  if (isLoading || !d) return <><LoadingGrid n={4} /><div className="mt-6"><LoadingBlock /></div></>;
  const k = d.kpis; const dd = k.csat_90d !== null && k.csat_prev_90d !== null ? k.csat_90d - k.csat_prev_90d : null;
  return <Page title="Customer Intelligence" sub="Who is slipping away, how concentrated profit is, and whether service quality is holding." fresh={d.freshness}>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
      <Stat label="Customers who bought (12 months)" value={num(k.customers_12m)} /><Stat label="Repeat rate" value={pct(k.repeat_rate, 0)} /><Stat label="Profit from top 10% of customers" value={pct(k.top10_share_gp, 0)} />
      <Stat label="Profit from overdue customers" value={egp(k.overdue_gp_12m)} tone="text-rose-600" /><Stat label="Overdue wholesale accounts" value={num(k.overdue_wholesale)} tone="text-amber-600" /></div>
    <Card className="p-5"><h3 className="font-semibold">{t("Customer status")}</h3><p className="text-xs text-slate-500">{t("Each customer is compared with their own buying rhythm")} · {t(d.window_label)}</p>
      <div className="mt-4 flex h-4 overflow-hidden rounded-full bg-slate-100">{d.segments.map((s: any) => <div key={s.status} title={`${t(s.status)} ${pct(s.share_gp, 0)}`} style={{ width: `${s.share_gp * 100}%`, background: SEG[s.status] }} />)}</div>
      <p className="mt-1 text-xs text-slate-400">{t("Bar = share of 12-month profit")}</p>
      <div className="mt-3 overflow-auto"><table className="w-full text-sm"><thead className="text-xs uppercase text-slate-500"><tr><th className="py-2 text-start">{t("Status")}</th><th className="text-end">{t("Customers")}</th><th className="text-end">{t("Share of customers")}</th><th className="text-end">{t("Profit (12 months)")}</th><th className="text-end">{t("Share of profit")}</th></tr></thead>
        <tbody className="divide-y divide-slate-100">{d.segments.map((s: any) => <tr key={s.status}><td className="py-2"><span className="inline-flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ background: SEG[s.status] }} />{t(s.status)}</span></td><td className="text-end">{num(s.customers)}</td><td className="text-end">{pct(s.share_customers, 0)}</td><td className="text-end">{egp(s.gp_12m)}</td><td className="text-end font-medium">{pct(s.share_gp, 0)}</td></tr>)}</tbody></table></div></Card>
    <Panel title="Who to contact first" hint="Valuable customers whose purchases are overdue compared with their own rhythm"><div className="overflow-auto"><table className="w-full text-sm"><thead className="text-xs uppercase text-slate-500"><tr>{["Customer", "Type", "Governorate", "Invoices", "Profit (12 months)", "Days since last order", "Usually every", "Status"].map((x, i) => <th key={x} className={`whitespace-nowrap py-2 pe-3 ${i < 3 || i === 7 ? "text-start" : "text-end"}`}>{t(x)}</th>)}</tr></thead>
      <tbody className="divide-y divide-slate-100">{d.accounts.map((a: any) => <tr key={a.customer_id}><td className="py-2 pe-3 font-medium">{a.customer_id}</td><td className="pe-3">{t(a.customer_type)}</td><td className="pe-3">{a.governorate || "—"}</td><td className="pe-3 text-end">{num(a.orders)}</td><td className="pe-3 text-end font-semibold">{egp(a.gp_12m)}</td>
        <td className="pe-3 text-end">{num(a.recency)}</td><td className="pe-3 text-end">{num(a.expected_gap, 0)} {t("d")}</td><td><Badge kind={a.status === "Lapsed" ? "CRITICAL" : "WARNING"}>{t(a.status)}</Badge></td></tr>)}</tbody></table></div></Panel>
    <div className="grid gap-4 xl:grid-cols-2">
      <Panel title="Acquisition source" hint="Retail customers by how they found the brand"><div className="overflow-auto"><table className="w-full text-sm"><thead className="text-xs uppercase text-slate-500"><tr><th className="py-2 text-start">{t("Source")}</th><th className="text-end">{t("Customers")}</th><th className="text-end">{t("Repeat rate")}</th><th className="text-end">{t("Profit per customer")}</th></tr></thead>
        <tbody className="divide-y divide-slate-100">{d.channels.map((c: any) => <tr key={c.acquisition_channel}><td className="py-2">{c.acquisition_channel}</td><td className="text-end">{num(c.customers)}</td><td className="text-end">{pct(c.repeat, 0)}</td><td className="text-end">{egp(c.gp_per_customer)}</td></tr>)}</tbody></table></div><p className="mt-3 rounded-xl bg-slate-50 p-3 text-xs text-slate-600">{d.channel_note}</p></Panel>
      <Panel title="Customer service" hint="Satisfaction (CSAT, 1 to 5)"><div className="mb-3 flex flex-wrap gap-6"><div><p className="text-xs text-slate-500">{t("Last 90 days")}</p><p className="text-2xl font-semibold">{k.csat_90d ?? "—"}</p></div><div><p className="text-xs text-slate-500">{t("Previous 90 days")}</p><p className="text-2xl font-semibold">{k.csat_prev_90d ?? "—"}</p></div>
        {dd !== null && <div><p className="text-xs text-slate-500">{t("Change")}</p><p className={`text-2xl font-semibold ${dd < 0 ? "text-rose-600" : "text-emerald-600"}`}>{dd > 0 ? "+" : ""}{dd.toFixed(2)}</p></div>}</div>
        <table className="w-full text-sm"><thead className="text-xs uppercase text-slate-500"><tr><th className="py-2 text-start">{t("Issue type")}</th><th className="text-end">{t("Tickets")}</th><th className="text-end">CSAT</th><th className="text-end">{t("Resolution (h)")}</th></tr></thead>
          <tbody className="divide-y divide-slate-100">{d.service_issues.map((s: any) => <tr key={s.issue_type}><td className="py-2">{s.issue_type}</td><td className="text-end">{num(s.tickets)}</td><td className="text-end font-medium">{num(s.csat, 2)}</td><td className="text-end">{num(s.resolution_h, 1)}</td></tr>)}</tbody></table></Panel></div>
    <Panel title="Read this first" hint="Limits"><ul className="list-disc space-y-1.5 ps-5 text-sm text-slate-600">{d.notes.map((n: string, i: number) => <li key={i}>{n}</li>)}</ul></Panel>
  </Page>;
}
