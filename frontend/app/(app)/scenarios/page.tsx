"use client";
import { useEffect, useMemo, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { egp, num, pct } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { Page, Panel } from "@/components/Page";
import { ErrorState, LoadingBlock } from "@/components/States";
import { Card, Input, Select } from "@/components/ui/primitives";
import { cn } from "@/lib/utils";

type Kind = "discount" | "extra_stock" | "material_price";
const TABS: { k: Kind; label: string; hint: string }[] = [
  { k: "discount", label: "Change a discount", hint: "What if I change the discount on a product in one channel?" },
  { k: "extra_stock", label: "Produce or order more", hint: "What if I make or buy more units of a product?" },
  { k: "material_price", label: "Material price changes", hint: "What if a material gets more (or less) expensive?" }];
const sgn = (v: number) => (v > 0 ? "text-emerald-600" : v < 0 ? "text-rose-600" : "text-slate-600");
const signed = (v: number, f: (x: number) => string) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${f(Math.abs(v))}`;

function Row({ label, a, b, fmt }: { label: string; a: number | null; b: number | null; fmt: (x: number) => string }) {
  const d = a !== null && b !== null ? b - a : 0;
  return <tr><td className="py-2 text-slate-600">{label}</td><td className="text-end">{a === null ? "—" : fmt(a)}</td><td className="text-end font-medium">{b === null ? "—" : fmt(b)}</td><td className={cn("text-end font-semibold", sgn(d))}>{a === null || b === null ? "—" : signed(d, fmt)}</td></tr>;
}

export default function Scenarios() {
  const { t } = useI18n(); const opt = useApi("/commercial/scenario/options");
  const [kind, setKind] = useState<Kind>("discount"); const [pid, setPid] = useState(""); const [channel, setChannel] = useState("Retail"); const [disc, setDisc] = useState<number | null>(null);
  const [lift, setLift] = useState(0); const [units, setUnits] = useState(500); const [mat, setMat] = useState(""); const [mpct, setMpct] = useState(15); const [pass, setPass] = useState(0);
  const [res, setRes] = useState<any>(null); const [err, setErr] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  const product = useMemo(() => opt.data?.products.find((p: any) => p.product_id === pid), [opt.data, pid]);
  const chInfo = product?.channels.find((c: any) => c.channel === channel);
  useEffect(() => { if (opt.data && !pid) { setPid(opt.data.products[0]?.product_id || ""); setMat(opt.data.materials[0]?.material_id || ""); } }, [opt.data, pid]);
  useEffect(() => { if (product && !product.channels.find((c: any) => c.channel === channel)) setChannel(product.channels[0]?.channel); }, [product, channel]);
  useEffect(() => { setDisc(chInfo?.avg_discount != null ? Math.round(chInfo.avg_discount * 100) : null); }, [pid, channel, chInfo?.avg_discount]);
  const body = useMemo(() => kind === "discount" ? (disc === null ? null : { product_id: pid, channel, new_discount: disc / 100, lift_per_5pp: lift / 100 })
    : kind === "extra_stock" ? { product_id: pid, extra_units: Math.max(1, Math.round(units || 0)) } : { material_id: mat, pct: mpct / 100, pass_through: pass / 100 }, [kind, pid, channel, disc, lift, units, mat, mpct, pass]);
  useEffect(() => {
    if (!body || !(pid || mat)) return; let live = true; setBusy(true);
    const id = setTimeout(() => api(`/commercial/scenario/${kind}`, { method: "POST", body: JSON.stringify(body) }).then((r) => { if (live) { setRes(r); setErr(null); } }).catch((e) => { if (live) { setRes(null); setErr(e.message); } }).finally(() => live && setBusy(false)), 400);
    return () => { live = false; clearTimeout(id); };
  }, [kind, body, pid, mat]);
  if (opt.error) return <ErrorState error={opt.error} retry={opt.refetch} />;
  if (opt.isLoading || !opt.data) return <LoadingBlock />;
  const lbl = "mb-1 block text-xs font-medium text-slate-600";
  return <Page title="What-if Scenarios" sub="Try a decision on paper before you make it. Every result lists its assumptions." fresh={opt.data.freshness}>
    <div className="grid gap-3 md:grid-cols-3">{TABS.map((x) => <button key={x.k} onClick={() => { setKind(x.k); setRes(null); setErr(null); }} className={cn("rounded-2xl border p-4 text-start transition", kind === x.k ? "border-brand-500 bg-brand-50 shadow-card" : "border-slate-200 bg-surface hover:border-slate-300")}>
      <p className="font-semibold">{t(x.label)}</p><p className="mt-1 text-xs text-slate-500">{t(x.hint)}</p></button>)}</div>
    <div className="grid gap-4 xl:grid-cols-[360px_1fr]">
      <Panel title="Your scenario" hint="Change a value and the result updates"><div className="space-y-4">
        {kind !== "material_price" && <div><label className={lbl}>{t("Product")}</label><Select className="w-full" value={pid} onChange={(e) => setPid(e.target.value)}>{opt.data.products.map((p: any) => <option key={p.product_id} value={p.product_id}>{p.product_name}</option>)}</Select></div>}
        {kind === "discount" && <>
          <div><label className={lbl}>{t("Channel")}</label><Select className="w-full" value={channel} onChange={(e) => setChannel(e.target.value)}>{product?.channels.map((c: any) => <option key={c.channel} value={c.channel}>{t(c.channel)}</option>)}</Select></div>
          <div><label className={lbl}>{t("New discount")}: <b>{disc ?? "—"}%</b> <span className="text-slate-400">({t("now")} {chInfo?.avg_discount != null ? pct(chInfo.avg_discount, 1) : "—"})</span></label><input type="range" min={0} max={60} step={1} value={disc ?? 0} onChange={(e) => setDisc(Number(e.target.value))} className="w-full accent-brand-600" /></div>
          <div><label className={lbl}>{t("Extra volume per +5 points of discount")}: <b>{lift}%</b></label><input type="range" min={0} max={100} step={5} value={lift} onChange={(e) => setLift(Number(e.target.value))} className="w-full accent-brand-600" />
            <p className="mt-1 text-xs text-slate-400">{t("The data shows no measurable lift in Retail and Online, so 0% is the supported starting point.")}</p></div></>}
        {kind === "extra_stock" && <div><label className={lbl}>{t("Extra units to produce or order")}</label><Input type="number" min={1} value={units} onChange={(e) => setUnits(Number(e.target.value))} /></div>}
        {kind === "material_price" && <>
          <div><label className={lbl}>{t("Material")}</label><Select className="w-full" value={mat} onChange={(e) => setMat(e.target.value)}>{opt.data.materials.map((m: any) => <option key={m.material_id} value={m.material_id}>{m.material_name}</option>)}</Select></div>
          <div><label className={lbl}>{t("Price change")}: <b>{mpct > 0 ? "+" : ""}{mpct}%</b></label><input type="range" min={-30} max={100} step={5} value={mpct} onChange={(e) => setMpct(Number(e.target.value))} className="w-full accent-brand-600" /></div>
          <div><label className={lbl}>{t("Recovered through selling prices")}: <b>{pass}%</b></label><input type="range" min={0} max={100} step={10} value={pass} onChange={(e) => setPass(Number(e.target.value))} className="w-full accent-brand-600" /></div></>}</div></Panel>
      <Card className="p-5">{busy && !res ? <LoadingBlock h="h-40" /> : err ? <p className="rounded-xl bg-rose-50 p-4 text-sm text-rose-700">{err}</p> : !res ? <p className="text-sm text-slate-500">{t("Choose a scenario to see the result.")}</p> : <div className={cn("space-y-4", busy && "opacity-60")}>
        <div><p className="text-xs font-semibold uppercase tracking-wide text-brand-700">{t("Result")}</p><h3 className="text-lg font-semibold">{res.title}</h3><p className="text-xs text-slate-500">{t("Next 90 days")}</p></div>
        {res.kind === "discount" && <>
          <table className="w-full text-sm"><thead className="text-xs uppercase text-slate-500"><tr><th className="text-start">&nbsp;</th><th className="text-end">{t("Today")}</th><th className="text-end">{t("Scenario")}</th><th className="text-end">{t("Change")}</th></tr></thead><tbody className="divide-y divide-slate-100">
            <Row label={t("Discount")} a={res.before.discount} b={res.after.discount} fmt={(x) => pct(x, 1)} /><Row label={t("Units")} a={res.before.units} b={res.after.units} fmt={(x) => num(x, 0)} />
            <Row label={t("Revenue")} a={res.before.revenue} b={res.after.revenue} fmt={(x) => egp(x)} /><Row label={t("Gross profit")} a={res.before.gross_profit} b={res.after.gross_profit} fmt={(x) => egp(x)} /><Row label={t("Margin")} a={res.before.margin} b={res.after.margin} fmt={(x) => pct(x, 1)} /></tbody></table>
          {res.breakeven_volume_change !== null && <div className="rounded-xl bg-slate-50 p-4 text-sm">{res.breakeven_volume_change >= 0 ? <>{t("To earn the same profit, volume must grow by")} <b>{pct(res.breakeven_volume_change, 0)}</b>.</> : <>{t("Volume can fall by up to")} <b>{pct(-res.breakeven_volume_change, 0)}</b> {t("before profit drops below today.")}</>}</div>}
          {res.warnings?.includes("margin_below_floor") && <p className="flex items-center gap-2 rounded-xl bg-amber-50 p-3 text-sm text-amber-800"><AlertTriangle className="h-4 w-4" />{t("The margin would fall below the configured floor.")}</p>}</>}
        {res.kind === "extra_stock" && <>
          <div className="grid gap-3 sm:grid-cols-3">{[["Units that would sell", num(res.units_needed, 0), "text-emerald-600"], ["Units left unsold", num(res.units_unused, 0), res.units_unused > 0 ? "text-amber-600" : ""], ["Net profit", signed(res.net_profit, (x) => egp(x)), sgn(res.net_profit)]].map(([l, v, c]) => <div key={l} className="rounded-xl border border-slate-100 p-3"><p className="text-xs text-slate-500">{t(l)}</p><p className={cn("mt-1 text-xl font-semibold", c)}>{v}</p></div>)}</div>
          <p className="text-sm text-slate-600">{t("Profit gained")}: <b>{egp(res.profit_gain)}</b> · {t("Cash tied up")}: <b>{egp(res.cash_tied_up)}</b> · {t("Holding cost")}: <b>{egp(res.holding_cost)}</b> · {t("Current gap")}: <b>{num(res.total_deficit, 0)} {t("units")}</b></p>
          <table className="w-full text-sm"><thead className="text-xs uppercase text-slate-500"><tr><th className="text-start">{t("Channel")}</th><th className="text-end">{t("Gap to cover")}</th><th className="text-end">{t("Extra units used")}</th></tr></thead><tbody className="divide-y divide-slate-100">{res.channels.map((c: any) => <tr key={c.channel}><td className="py-2">{t(c.channel)}</td><td className="text-end">{num(c.deficit, 0)}</td><td className="text-end font-medium">{num(c.units_used, 0)}</td></tr>)}</tbody></table></>}
        {res.kind === "material_price" && <>
          <div className="grid gap-3 sm:grid-cols-3"><div className="rounded-xl border border-slate-100 p-3"><p className="text-xs text-slate-500">{t("Profit impact")}</p><p className={cn("mt-1 text-xl font-semibold", sgn(res.profit_impact))}>{signed(res.profit_impact, (x) => egp(x))}</p></div>
            <div className="rounded-xl border border-slate-100 p-3"><p className="text-xs text-slate-500">{t("Share of 90-day profit")}</p><p className="mt-1 text-xl font-semibold">{res.impact_share === null ? "—" : signed(res.impact_share, (x) => pct(x, 1))}</p></div>
            <div className="rounded-xl border border-slate-100 p-3"><p className="text-xs text-slate-500">{t("Products affected")}</p><p className="mt-1 text-xl font-semibold">{num(res.products_affected)}</p></div></div>
          <table className="w-full text-sm"><thead className="text-xs uppercase text-slate-500"><tr><th className="text-start">{t("Most affected products")}</th><th className="text-end">{t("Cost per unit")}</th><th className="text-end">{t("Profit impact")}</th></tr></thead><tbody className="divide-y divide-slate-100">{res.top_products.map((p: any) => <tr key={p.product_id}><td className="py-2">{p.product_name}</td><td className="text-end">{signed(p.cost_per_unit_change, (x) => egp(x, false))}</td><td className={cn("text-end font-medium", sgn(p.profit_impact))}>{signed(p.profit_impact, (x) => egp(x))}</td></tr>)}</tbody></table></>}
        <div className="border-t border-slate-100 pt-3"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t("Assumptions")}</p><ul className="mt-1 list-disc space-y-1 ps-5 text-xs text-slate-500">{res.assumptions?.map((a: string, i: number) => <li key={i}>{a}</li>)}</ul></div></div>}</Card></div>
  </Page>;
}
