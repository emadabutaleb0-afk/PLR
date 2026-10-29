"use client";
import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Boxes, Download, Flame, PackageX, ShieldAlert, TrendingUp, Truck } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import { api, download } from "@/lib/api";
import { egp, greetingKey, num, pct } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useCompany } from "@/lib/company";
import { Freshness } from "@/components/Freshness";
import { KpiCard, DecisionCard } from "@/components/Cards";
import { ErrorState, LoadingGrid, Empty, LoadingBlock } from "@/components/States";
import { RecDialog } from "@/components/RecDialog";
import { LogoBadge } from "@/components/Brand";
import { Badge, Card } from "@/components/ui/primitives";
import { LEAK_COLOR } from "@/components/leak";

const TONE: Record<string, { text: string; bar: string; icon: any }> = {
  rose: { text: "text-rose-600", bar: "bg-rose-500", icon: ShieldAlert }, emerald: { text: "text-emerald-600", bar: "bg-emerald-500", icon: TrendingUp }, amber: { text: "text-amber-600", bar: "bg-amber-500", icon: PackageX },
  violet: { text: "text-violet-600", bar: "bg-violet-500", icon: Boxes }, slate: { text: "text-slate-700", bar: "bg-slate-700", icon: Flame }, sky: { text: "text-sky-600", bar: "bg-sky-500", icon: Truck },
};

export default function Home() {
  const { t, isAr } = useI18n(); const { user, can } = useAuth(); const { companyName } = useCompany(); const ex = can("executive");
  const cc = useApi(ex ? "/commercial/command-center" : null); const lk = useApi(ex ? "/commercial/leakage" : null); const ov = useApi(ex ? "/executive/overview" : null); const dec = useApi(ex ? "/executive/decisions?limit=6" : null);
  const [open, setOpen] = useState<any>(null); const [busy, setBusy] = useState<string | null>(null);
  const first = (user?.full_name || user?.email || "").split(/[ @]/)[0]; const Arrow = isAr ? ArrowLeft : ArrowRight;
  const head = ["revenue", "gross_profit", "gross_margin", "return_cost", "marketing_efficiency"];
  const review = async (a: any) => { if (!a.rec_key) return; setBusy(a.rec_key); try { setOpen(await api(`/recommendations/${encodeURIComponent(a.rec_key).replace(/%3A/g, ":")}`)); } finally { setBusy(null); } };
  return <div className="space-y-8">
    <section className="brand-grad relative overflow-hidden rounded-3xl p-6 text-white shadow-card lg:p-8">
      <div className="flex flex-wrap items-center gap-5"><LogoBadge size={64} /><div className="min-w-0 flex-1">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-brand-200">{t("Command Center")}</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight lg:text-3xl">{t(greetingKey())}{first ? `, ${first}` : ""}</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-300 lg:text-base">{t("Where is {company} losing money today, what will happen next, and what should the business do about it?", { company: companyName })}</p></div>
        <div className="flex flex-col items-end gap-2"><div className="rounded-xl bg-white/10 px-3 py-2 text-xs text-slate-200"><Freshness dark f={cc.data?.freshness || ov.data?.freshness} /></div>
          {ex && <button onClick={() => download("/commercial/weekly-report.pdf", "merchbrain-weekly-report.pdf")} className="inline-flex items-center gap-2 rounded-xl border border-white/20 bg-white/10 px-3 py-2 text-sm font-medium text-white hover:bg-white/20"><Download className="h-4 w-4" />{t("Weekly report (PDF)")}</button>}</div></div></section>
    {!ex && <Card className="p-6 text-sm text-slate-600">{t("Use the menu to open your areas:")} <Link className="text-brand-600 underline" href="/alerts">{t("Alert Center")}</Link>, <Link className="text-brand-600 underline" href="/actions">{t("Action Center")}</Link>, <Link className="text-brand-600 underline" href="/products">{t("Products")}</Link>.</Card>}
    {ex && (cc.isLoading ? <LoadingGrid n={6} /> : cc.error ? <ErrorState error={cc.error} retry={cc.refetch} /> : <>
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-6">{cc.data.tiles.map((k: any) => { const tn = TONE[k.tone] || TONE.slate; const Icon = tn.icon;
        return <Card key={k.key} className="relative overflow-hidden p-4"><span className={`absolute inset-x-0 top-0 h-1 ${tn.bar}`} /><div className="flex items-start justify-between gap-2"><p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{t(k.label)}</p><Icon className={`h-4 w-4 ${tn.text}`} /></div>
          <p className={`mt-2 text-2xl font-semibold tracking-tight ${tn.text}`}>{k.unit === "egp" ? egp(k.value) : <>{num(k.value)} <span className="text-sm font-normal text-slate-500">{t(k.unit)}</span></>}</p><p className="mt-1.5 text-xs leading-snug text-slate-400">{k.note}</p></Card>; })}</section>
      <section><div className="mb-3 flex items-end justify-between"><h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">{t("Top actions today")}</h2></div>
        <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">{cc.data.actions.map((a: any, i: number) => <Card key={a.slot} className="flex flex-col gap-3 p-5">
          <div className="flex items-center gap-3"><span className="grid h-8 w-8 place-items-center rounded-full bg-ink-900 text-sm font-semibold text-brand-200">{i + 1}</span><div className="flex-1"><p className="text-xs font-semibold uppercase tracking-wide text-brand-700">{t(a.label)}</p></div><Badge kind={a.urgency}>{t(a.urgency)}</Badge></div>
          <h3 className="font-semibold leading-snug">{a.title}</h3><p className="text-sm text-slate-600">{a.detail}</p>{a.why && <p className="text-xs text-slate-500">{a.why}</p>}
          <div className="mt-auto flex items-end justify-between gap-3 border-t border-slate-100 pt-3"><div><p className="text-xs text-slate-500">{t(a.value_kind)}</p><p className="text-lg font-semibold text-ink">{egp(a.value_egp)}</p></div>
            {a.rec_key ? <button onClick={() => review(a)} disabled={busy === a.rec_key} className="inline-flex items-center gap-1.5 rounded-xl bg-accent px-3 py-2 text-sm font-medium text-accent-fg hover:bg-accent-hover disabled:opacity-60">{t("Review & decide")}<Arrow className="h-4 w-4" /></button>
              : <Link href={a.page} className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium hover:bg-slate-50">{t("Open")}<Arrow className="h-4 w-4" /></Link>}</div></Card>)}</div></section></>)}
    {ex && <section className="grid gap-4 xl:grid-cols-3">
      <Card className="p-5 xl:col-span-2"><div className="mb-3 flex items-end justify-between"><div><h3 className="font-semibold">{t("Where the money leaks")}</h3><p className="text-xs text-slate-500">{lk.data ? t(lk.data.window_label) : ""}</p></div><Link href="/leakage" className="text-sm font-medium text-brand-700 hover:underline">{t("Open Profit Leakage")}</Link></div>
        {lk.isLoading ? <LoadingBlock h="h-32" /> : lk.error ? <ErrorState error={lk.error} retry={lk.refetch} /> : <>
          <p className="text-3xl font-semibold tracking-tight">{egp(lk.data.total)} <span className="text-sm font-normal text-slate-500">{t("leaked in the last 12 months")}</span></p>
          <div className="mt-4 flex h-3 overflow-hidden rounded-full bg-slate-100">{lk.data.items.map((i: any) => <div key={i.key} title={`${t(i.label)} ${pct(i.share, 0)}`} style={{ width: `${(i.share || 0) * 100}%`, background: LEAK_COLOR[i.key] }} />)}</div>
          <div className="mt-4 grid gap-x-6 gap-y-2 sm:grid-cols-2">{lk.data.items.map((i: any) => <div key={i.key} className="flex items-center justify-between gap-3 text-sm"><span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ background: LEAK_COLOR[i.key] }} />{i.label}</span><span className="font-medium">{egp(i.value)} <span className="text-xs text-slate-400">{pct(i.share, 0)}</span></span></div>)}</div></>}</Card>
      <Card className="p-5"><h3 className="font-semibold">{t("Business health")}</h3><p className="text-xs text-slate-500">{ov.data ? t(ov.data.period_label) : ""}</p>
        {ov.isLoading ? <LoadingBlock h="h-32" /> : ov.data && <div className="mt-3 divide-y divide-slate-100">{head.map((k) => { const x = ov.data.kpis.find((y: any) => y.key === k); if (!x) return null; const v = x.unit === "pct" ? pct(x.value) : x.unit === "x" ? `${x.value?.toFixed(1)}x` : egp(x.value);
          return <div key={k} className="flex items-center justify-between py-2 text-sm"><span className="text-slate-600">{t(x.label)}</span><span className="text-end"><span className="font-semibold">{v}</span>{x.change !== null && x.change !== undefined && <span className={`ms-2 text-xs ${x.change >= 0 ? "text-emerald-600" : "text-rose-600"}`}>{x.change >= 0 ? "+" : "−"}{pct(Math.abs(x.change), 0)}</span>}</span></div>; })}</div>}</Card></section>}
    {ex && <section><h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">{t("What needs your attention today?")}</h2>
      {dec.isLoading ? <LoadingGrid n={3} /> : dec.error ? <ErrorState error={dec.error} retry={dec.refetch} /> : dec.data.items.length === 0 ? <Empty title="No open decisions" hint="Everything has been decided, or no data has been imported yet." /> :
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{dec.data.items.map((d: any) => <DecisionCard key={d.rec_key} d={d} onOpen={setOpen} />)}</div>}</section>}
    {open && <RecDialog rec={open} onClose={() => setOpen(null)} />}</div>;
}
