"use client";
import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Bar, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Save, Trash2 } from "lucide-react";
import { useApi } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n";
import { useWorkspace } from "@/lib/workspace";
import { METRIC } from "@/lib/metrics";
import { egp, num, pct } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Page } from "@/components/Page";
import { ProductPicker } from "@/components/ProductPicker";
import { axis } from "@/components/Chart";
import { Badge, Button, Card, Input, Select } from "@/components/ui/primitives";
import { Empty, ErrorState, LoadingBlock } from "@/components/States";
import { SplitPane, Timeline } from "@/components/ui/layout";

const PANELS = [["sales", "Sales"], ["inventory", "Inventory"], ["returns", "Returns"], ["supply", "Supplier chain"], ["production", "Production"], ["decisions", "Decisions"], ["locations", "Locations"]] as const;
type Kind = (typeof PANELS)[number][0];
const kfmt = (v: number) => (Math.abs(v) >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : Math.abs(v) >= 1e3 ? `${(v / 1e3).toFixed(0)}K` : String(v));

function Body({ kind, product, location, month, setMonth, setLocation }: { kind: Kind; product: string; location: string; month: string | null; setMonth: (m: string) => void; setLocation: (l: string) => void }) {
  const { t } = useI18n();
  const tl = useApi<any>(["sales", "inventory", "production"].includes(kind) ? `/workspace/timeline?product_id=${product}${location ? `&location_id=${location}` : ""}` : null);
  const ctx = useApi<any>(["returns", "supply", "production", "decisions"].includes(kind) ? `/workspace/products/${product}/context` : null);
  const det = useApi<any>(kind === "locations" ? `/products/${product}` : null);
  const err = tl.error || ctx.error || det.error; if (err) return <ErrorState error={err} retry={() => { tl.refetch(); ctx.refetch(); det.refetch(); }} />;
  if ((tl.isLoading && ["sales", "inventory", "production"].includes(kind)) || (ctx.isLoading && ctx.fetchStatus !== "idle") || (det.isLoading && det.fetchStatus !== "idle")) return <LoadingBlock h="h-64" />;
  const chart = (keys: string[], bars: string[]) => { const months = tl.data?.months || []; if (!months.length) return <Empty title="No history for this selection" />;
    const ks = keys.filter((k) => tl.data.coverage[k]); if (!ks.length) return <Empty title="No history for this selection" hint="This role or selection has no figures for this panel." />;
    return <div className="chart-ltr h-64 w-full"><ResponsiveContainer><ComposedChart data={months} syncId="inv" onClick={(e: any) => e?.activeLabel && setMonth(e.activeLabel)}><CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" /><XAxis dataKey="month" tick={axis} minTickGap={28} />
      <YAxis yAxisId="l" tick={axis} width={52} tickFormatter={kfmt} /><YAxis yAxisId="r" orientation="right" tick={axis} width={40} hide={ks.every((k) => bars.includes(k) || METRIC[k].unit === METRIC[ks[0]].unit)} />
      <Tooltip formatter={(v: any, n: any) => [METRIC[n]?.fmt(v), t(METRIC[n]?.label || n)]} contentStyle={{}} /><Legend formatter={(v) => t(METRIC[v]?.label || v)} />
      {ks.map((k, i) => bars.includes(k) ? <Bar key={k} yAxisId="l" dataKey={k} fill="var(--series-gold)" radius={[4, 4, 0, 0]} maxBarSize={20} isAnimationActive={false} /> : <Line key={k} yAxisId={METRIC[k].unit === METRIC[ks[0]].unit ? "l" : "r"} dataKey={k} stroke={i ? "var(--c-sky)" : "var(--series-ink)"} strokeWidth={2} dot={false} isAnimationActive={false} />)}
      {month && <ReferenceLine yAxisId="l" x={month} stroke="var(--c-red)" strokeWidth={2} />}</ComposedChart></ResponsiveContainer></div>; };
  if (kind === "sales") return chart(["net_sales_egp", "refunds_egp"], ["net_sales_egp"]);
  if (kind === "inventory") return chart(["closing_stock_units", "stockout_days"], ["closing_stock_units"]);
  if (kind === "production") return <div className="space-y-3">{tl.data && chart(["units_produced", "units_rejected"], ["units_produced"])}{ctx.data?.production_orders ? <div className="overflow-x-auto"><table className="w-full text-xs"><thead className="text-slate-500"><tr>{["Order", "Completed", "Good", "Rejected", "Efficiency", "Delay (days)", "Bottleneck"].map((h) => <th key={h} scope="col" className="p-1.5 text-start font-medium">{t(h)}</th>)}</tr></thead><tbody className="divide-y divide-line">{ctx.data.production_orders.map((o: any) => <tr key={o.production_order_id}><td className="p-1.5">{o.production_order_id}</td><td className="num p-1.5">{o.completion_date ?? "—"}</td><td className="num p-1.5">{num(o.good_qty)}</td><td className="num p-1.5">{num(o.rejected_qty)}</td><td className="num p-1.5">{num(o.efficiency_pct, 1)}%</td><td className="num p-1.5">{num(o.delay_days)}</td><td className="p-1.5">{o.primary_bottleneck ?? "—"}</td></tr>)}</tbody></table></div> : null}</div>;
  if (kind === "returns") { const r = ctx.data?.returns || []; if (!r.length) return <Empty title="No returns recorded" />; const max = Math.max(...r.map((x: any) => x.lines));
    return <ul className="space-y-2 text-sm">{r.map((x: any) => <li key={x.reason}><div className="flex justify-between"><span>{x.reason}</span><span className="tabular text-slate-600">{num(x.lines)} {t("lines")} · {egp(x.refund_egp)}{x.quality_related ? ` · ${num(x.quality_related)} ${t("quality-related")}` : ""}</span></div><div className="mt-1 h-1.5 rounded-full bg-sunken"><div className="h-full rounded-full bg-rose-500" style={{ width: `${(x.lines / max) * 100}%` }} /></div></li>)}</ul>; }
  if (kind === "supply") { const p = ctx.data?.procurement; if (!p) return <Empty title="Procurement details are not available to your role" />; if (!p.length) return <Empty title="No bill of materials for this product" />;
    return <div className="space-y-3">{p.map((m: any) => <div key={m.material_id} className="rounded-xl border border-line p-3"><p className="text-sm font-semibold">{m.material_name} <span className="text-xs font-normal text-slate-500">{num(m.required_per_unit, 2)} {m.unit} / {t("unit")}</span></p>
      {m.suppliers.length ? <table className="mt-1 w-full text-xs"><thead className="text-slate-500"><tr><th scope="col" className="py-1 text-start font-medium">{t("Supplier")}</th><th scope="col" className="py-1 text-end font-medium">{t("Orders")}</th><th scope="col" className="py-1 text-end font-medium">{t("Rejected")}</th><th scope="col" className="py-1 text-end font-medium">{t("Avg delay (days)")}</th></tr></thead>
        <tbody>{m.suppliers.map((s: any) => <tr key={s.supplier_id}><td className="py-1">{s.supplier_name}</td><td className="num py-1 text-end">{num(s.purchase_orders)}</td><td className="num py-1 text-end">{s.rejected_rate == null ? "—" : pct(s.rejected_rate)}</td><td className="num py-1 text-end">{s.avg_delay_days ?? "—"}</td></tr>)}</tbody></table> : <p className="mt-1 text-xs text-slate-500">{t("No purchase orders recorded for this material.")}</p>}</div>)}</div>; }
  if (kind === "decisions") { const h = ctx.data?.decision_history || []; if (!h.length) return <Empty title="No decisions for this product" />;
    return <ul className="divide-y divide-line text-sm">{h.map((r: any) => <li key={r.rec_key} className="flex items-center gap-3 py-2"><Badge kind={r.status === "ACCEPTED" ? "DONE" : r.status === "REJECTED" ? "FAILED" : r.status === "DEFERRED" ? "WATCH" : "NEW"}>{t(r.status)}</Badge><Link href={`/war-room?open=${encodeURIComponent(r.rec_key)}`} className="min-w-0 flex-1 truncate hover:underline">{r.title}</Link><span className="tabular text-xs text-slate-500">{egp(r.estimated_value_egp)} {r.is_estimate ? `(${t("estimate")})` : ""}</span></li>)}</ul>; }
  const ls: any[] = det.data?.locations || []; if (!ls.length) return <Empty title="No locations" />;
  return <div className="overflow-x-auto"><table className="w-full text-sm"><thead className="text-xs text-slate-500"><tr>{["Location", "Stock", "Units (12m)", "Days of cover"].map((h) => <th key={h} scope="col" className="p-2 text-start font-medium">{t(h)}</th>)}</tr></thead>
    <tbody className="divide-y divide-line">{ls.map((l) => <tr key={l.location_id} className={cn(location === l.location_id && "bg-accent/10")}><th scope="row" className="p-2 text-start font-medium"><button onClick={() => setLocation(location === l.location_id ? "" : l.location_id)} aria-pressed={location === l.location_id} className="text-start hover:underline">{l.location_name}</button></th><td className="num p-2">{num(l.closing_stock)}</td><td className="num p-2">{num(l.units_12m)}</td><td className="num p-2">{num(l.days_of_cover, 0)}</td></tr>)}</tbody></table>
    <p className="mt-2 text-xs text-slate-500">{t("Click a location to filter every panel to it.")}</p></div>;
}

function Panelled({ side, kind, setKind, ...rest }: { side: string; kind: Kind; setKind: (k: Kind) => void; product: string; location: string; month: string | null; setMonth: (m: string) => void; setLocation: (l: string) => void }) {
  const { t } = useI18n();
  return <Card className="min-h-[24rem] p-4"><div className="mb-3 flex items-center gap-2"><label className="sr-only" htmlFor={`k-${side}`}>{t("Panel")}</label><Select id={`k-${side}`} value={kind} onChange={(e) => setKind(e.target.value as Kind)} className="font-semibold">{PANELS.map(([k, l]) => <option key={k} value={k}>{t(l)}</option>)}</Select></div><Body kind={kind} {...rest} /></Card>;
}

function Workspace() {
  const { t } = useI18n(); const sp = useSearchParams(); const router = useRouter(); const ws = useWorkspace();
  const product = sp.get("product") || ws.productId; const location = sp.get("location") || ws.locationId || "";
  const [left, setLeft] = useState<Kind>("sales"); const [right, setRight] = useState<Kind>("inventory"); const [split, setSplit] = useState(52); const [month, setMonth] = useState<string | null>(null); const [name, setName] = useState<string | null>(null); const [lname, setLname] = useState("");
  useEffect(() => { ws.selectProduct(sp.get("product") || ws.productId); if (sp.get("location")) ws.selectLocation(sp.get("location")); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const head = useApi<any>(product ? `/products/${product}` : null); const opts = useApi<any>("/workspace/scope-options");
  const nav = (k: string, v: string | null) => { const p = new URLSearchParams(sp.toString()); v ? p.set(k, v) : p.delete(k); router.replace(`/investigate?${p}`); };
  const pickProduct = (id: string | null, n?: string) => { setName(n || null); ws.selectProduct(id); setMonth(null); nav("product", id); };
  const setLoc = (l: string) => { ws.selectLocation(l || null); nav("location", l || null); };
  const apply = (l: any) => { setLeft(l.layout.left); setRight(l.layout.right); setSplit(l.layout.split); if (l.layout.product) { ws.selectProduct(l.layout.product); const p = new URLSearchParams(); p.set("product", l.layout.product); if (l.layout.location) p.set("location", l.layout.location); router.replace(`/investigate?${p}`); } };
  const save = () => { if (!lname.trim()) return; ws.saveLayout(lname.trim(), { left, right, split, product, location }); setLname(""); };
  const h = head.data?.header;
  return <div className="space-y-4">
    <Card className="grid gap-3 p-4 md:grid-cols-[2fr_1fr_auto]"><div><span className="mb-1 block text-xs font-medium text-slate-600">{t("Product under investigation")}</span><ProductPicker value={product} label={name || h?.product_name} onPick={pickProduct} /></div>
      <label className="text-xs font-medium text-slate-600">{t("Location filter")}<Select className="mt-1 h-10 w-full" value={location} onChange={(e) => setLoc(e.target.value)}><option value="">{t("All locations")}</option>{opts.data?.locations.map((l: any) => <option key={l.location_id} value={l.location_id}>{l.location_name}</option>)}</Select></label>
      {product && <div className="flex items-end gap-2 text-xs"><Link href={`/products/${product}`} className="rounded-lg border border-line px-2.5 py-2 font-medium hover:bg-sunken">{t("Product 360")}</Link><Link href={`/time-machine?product=${product}`} className="rounded-lg border border-line px-2.5 py-2 font-medium hover:bg-sunken">{t("Time Machine")}</Link></div>}</Card>
    {!product ? <Empty title="Choose a product to start" hint="Pick a product above. Both panels, the location filter and the selected month stay linked while you investigate." /> : <>
      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">{month ? <span className="rounded-full bg-sunken px-2.5 py-1">{t("Selected month")}: <b className="tabular">{month}</b> <button onClick={() => setMonth(null)} className="ms-1 underline">{t("clear")}</button></span> : <span>{t("Click a month on any chart to mark it in both panels.")}</span>}{location && <span className="rounded-full bg-sunken px-2.5 py-1">{t("Filtered to")} {opts.data?.locations.find((l: any) => l.location_id === location)?.location_name ?? location}</span>}</div>
      <SplitPane label="Resize panels" value={split} onChange={setSplit} left={<Panelled side="l" kind={left} setKind={setLeft} product={product} location={location} month={month} setMonth={setMonth} setLocation={setLoc} />} right={<Panelled side="r" kind={right} setKind={setRight} product={product} location={location} month={month} setMonth={setMonth} setLocation={setLoc} />} />
      <Card className="p-4"><h2 className="text-sm font-semibold">{t("Saved layouts")}</h2><p className="text-xs text-slate-500">{t("Saved in this browser only. Another computer or user will not see them.")}</p>
        <div className="mt-2 flex flex-wrap gap-2"><Input className="max-w-xs" placeholder={t("Name this layout")} value={lname} onChange={(e) => setLname(e.target.value)} onKeyDown={(e) => e.key === "Enter" && save()} aria-label={t("Layout name")} /><Button variant="outline" onClick={save} disabled={!lname.trim()}><Save className="h-4 w-4" />{t("Save")}</Button></div>
        {!!ws.layouts.length && <ul className="mt-3 flex flex-wrap gap-2">{ws.layouts.map((l) => <li key={l.id} className="flex items-center rounded-full border border-line bg-surface text-xs"><button onClick={() => apply(l)} className="px-3 py-1.5 font-medium hover:underline">{l.name}</button><button onClick={() => ws.deleteLayout(l.id)} aria-label={`${t("Delete")} ${l.name}`} className="rounded-full p-1.5 text-slate-500 hover:text-rose-600"><Trash2 className="h-3.5 w-3.5" /></button></li>)}</ul>}</Card></>}
  </div>;
}
export default function Investigate() { return <Page title="Investigation Workspace" sub="Compare sales, stock, returns, suppliers and production for one product in linked panels."><Suspense fallback={<LoadingBlock />}><Workspace /></Suspense></Page>; }
