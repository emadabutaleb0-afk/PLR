"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Download } from "lucide-react";
import { download } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { egp, num, pct } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { LogoBadge } from "@/components/Brand";
import { ErrorState, LoadingBlock } from "@/components/States";
import { LEAK_COLOR } from "@/components/leak";
import { cn } from "@/lib/utils";

const STEPS = [
  { en: "The question", ar: "السؤال" }, { en: "Where we lose money", ar: "أين نخسر" }, { en: "What happens next", ar: "ماذا سيحدث" },
  { en: "What to do today", ar: "ماذا نفعل اليوم" }, { en: "What the data taught us", ar: "ماذا علّمتنا البيانات" }, { en: "Try it, and what we do not claim", ar: "جرّبه، وما لا ندّعيه" }];

export default function Demo() {
  const { t, isAr } = useI18n(); const L = isAr ? "ar" : "en"; const [i, setI] = useState(0);
  const cc = useApi("/commercial/command-center"); const lk = useApi("/commercial/leakage"); const ds = useApi("/commercial/discounts"); const cu = useApi("/commercial/customers"); const op = useApi("/operations/bottlenecks");
  const Next = isAr ? ArrowLeft : ArrowRight; const Prev = isAr ? ArrowRight : ArrowLeft;
  const go = useCallback((d: number) => setI((x) => Math.max(0, Math.min(STEPS.length - 1, x + d))), []);
  useEffect(() => { const f = (e: KeyboardEvent) => { if (e.key === "ArrowRight") go(isAr ? -1 : 1); if (e.key === "ArrowLeft") go(isAr ? 1 : -1); }; window.addEventListener("keydown", f); return () => window.removeEventListener("keydown", f); }, [go, isAr]);
  const ready = cc.data && lk.data && ds.data && cu.data && op.data;
  const big = "text-5xl font-semibold tracking-tight lg:text-6xl"; const sub = "mt-3 max-w-3xl text-lg text-slate-300";
  const tile = (k: string) => cc.data?.tiles.find((x: any) => x.key === k);
  let body: any = <LoadingBlock h="h-64" />;
  const failed = [cc, lk, ds, cu, op].find((q) => q.isError); // a role without access to these areas sees a clear message, not a blank story
  if (failed) body = <div className="rounded-2xl bg-surface p-2 text-slate-900"><ErrorState error={failed.error} retry={() => failed.refetch()} /></div>;
  if (ready && !failed) {
    const topLeak = lk.data.items[0]; const dl = op.data.downtime_link; const k = cu.data.kpis;
    body = [
      <div key="0" className="flex flex-col items-start gap-6"><LogoBadge size={96} /><h1 className="max-w-4xl text-3xl font-semibold leading-snug lg:text-5xl">{t("Where is El-Sharnouby losing money today, what will happen next, and what should the business do about it?")}</h1>
        <p className={sub}>{L === "ar" ? "ميرش برين يربط المبيعات والمخزون والمصنع والخامات والموردين والعملاء في مكان واحد، ويخرج بقرارات جاهزة." : "MerchBrain connects sales, stock, factory, materials, suppliers and customers in one place and ends with decisions, not charts."}</p></div>,
      <div key="1"><p className={sub}>{L === "ar" ? "تسرّبت من الأرباح خلال آخر 12 شهرًا" : "Leaked from profit in the last 12 months"}</p><p className={cn(big, "text-rose-400")}>{egp(lk.data.total)}</p>
        <div className="mt-6 flex h-4 max-w-3xl overflow-hidden rounded-full bg-white/10">{lk.data.items.map((x: any) => <div key={x.key} style={{ width: `${x.share * 100}%`, background: LEAK_COLOR[x.key] }} />)}</div>
        <div className="mt-4 grid max-w-3xl gap-2 sm:grid-cols-2">{lk.data.items.map((x: any) => <p key={x.key} className="flex items-center justify-between text-slate-300"><span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ background: LEAK_COLOR[x.key] }} />{x.label}</span><b className="text-white">{egp(x.value)}</b></p>)}</div>
        <p className={sub}>{L === "ar" ? `أكبر مصدر: ${topLeak.label} (${pct(topLeak.share, 0)}). الأرقام معلّمة كمسجّلة أو تقدير أو تعرّض.` : `Biggest source: ${topLeak.label} (${pct(topLeak.share, 0)}). Every figure is labelled recorded, estimate or exposure.`}</p></div>,
      <div key="2"><p className={sub}>{L === "ar" ? "إذا لم نتحرك" : "If nothing changes"}</p><p className={cn(big, "text-amber-300")}>{egp(tile("profit_at_risk")?.value)}</p><p className={sub}>{t("Profit at Risk")}</p>
        <div className="mt-6 grid max-w-4xl gap-4 sm:grid-cols-3">{["stockout_risk", "overstock_risk", "supply_risks"].map((key) => { const x = tile(key); return <div key={key} className="rounded-2xl border border-white/10 bg-white/5 p-5"><p className="text-xs uppercase tracking-wide text-slate-400">{t(x.label)}</p><p className="mt-2 text-4xl font-semibold">{num(x.value)}</p><p className="text-sm text-slate-400">{t(x.unit)}</p></div>; })}</div></div>,
      <div key="3"><div className="grid gap-3 lg:grid-cols-2">{cc.data.actions.map((a: any, n: number) => <div key={a.slot} className="rounded-2xl border border-white/10 bg-white/5 p-4"><p className="text-xs font-semibold uppercase tracking-wide text-brand-200">{n + 1} · {t(a.label)}</p><p className="mt-1 font-semibold">{a.title}</p><p className="mt-1 text-sm text-slate-300">{a.detail}</p><p className="mt-2 text-sm text-slate-400">{t(a.value_kind)}: <b className="text-white">{egp(a.value_egp)}</b></p></div>)}</div></div>,
      <div key="4" className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-5"><p className="text-xs uppercase tracking-wide text-brand-200">{t("Discount Intelligence")}</p><p className="mt-2 text-lg font-semibold leading-snug">{ds.data.headline}</p><p className="mt-3 text-sm text-slate-400">{t("Discount given above the comfort band")}: <b className="text-white">{egp(ds.data.excess_total)}</b></p></div>
        <div className="rounded-2xl border border-white/10 bg-white/5 p-5"><p className="text-xs uppercase tracking-wide text-brand-200">{t("Customer Intelligence")}</p><p className="mt-2 text-lg font-semibold leading-snug">{L === "ar" ? `${pct(k.top10_share_gp, 0)} من الربح من أعلى 10% من العملاء، و${num(k.overdue_wholesale)} حساب جملة متأخر عن إيقاعه.` : `${pct(k.top10_share_gp, 0)} of profit comes from the top 10% of customers, and ${num(k.overdue_wholesale)} wholesale accounts are overdue against their own rhythm.`}</p><p className="mt-3 text-sm text-slate-400">{t("Profit from overdue customers")}: <b className="text-white">{egp(k.overdue_gp_12m)}</b></p></div>
        <div className="rounded-2xl border border-white/10 bg-white/5 p-5"><p className="text-xs uppercase tracking-wide text-brand-200">{t("Operations Control")}</p><p className="mt-2 text-lg font-semibold leading-snug">{dl.verdict}</p><p className="mt-3 text-sm text-slate-400">{t("Monthly correlation")}: <b className="text-white">{dl.correlation ?? "—"}</b></p></div></div>,
      <div key="5"><div className="grid gap-4 lg:grid-cols-2"><div className="rounded-2xl border border-white/10 bg-white/5 p-5"><p className="text-xs uppercase tracking-wide text-brand-200">{L === "ar" ? "جرّبه" : "Try it"}</p>
          <div className="mt-3 flex flex-wrap gap-3"><Link href="/scenarios" className="rounded-xl bg-surface px-4 py-2 text-sm font-medium text-ink hover:bg-slate-100">{t("What-if Scenarios")}</Link><Link href="/allocation" className="rounded-xl border border-white/20 px-4 py-2 text-sm font-medium hover:bg-white/10">{t("Channel Allocation")}</Link>
            <button onClick={() => download("/commercial/weekly-report.pdf", "merchbrain-weekly-report.pdf")} className="inline-flex items-center gap-2 rounded-xl border border-white/20 px-4 py-2 text-sm font-medium hover:bg-white/10"><Download className="h-4 w-4" />{t("Weekly report (PDF)")}</button>
            <Link href="/method" className="rounded-xl border border-white/20 px-4 py-2 text-sm font-medium hover:bg-white/10">{t("How numbers are calculated")}</Link></div></div>
        <div className="rounded-2xl border border-amber-300/30 bg-amber-300/10 p-5"><p className="text-xs uppercase tracking-wide text-amber-200">{L === "ar" ? "ما لا ندّعيه" : "What we do not claim"}</p><ul className="mt-2 list-disc space-y-1.5 ps-5 text-sm text-slate-200">
          {(L === "ar" ? ["الأرقام تقديرات مبنية على ملفات التدريب، وبعض الملفات نموذجية.", "لم نثبت مرونة سعرية سببية: الخصم لم يرفع الكميات في التجزئة والأونلاين.", "لا توجد بيانات لمخزون الخامات، فنعرض الاحتياج والموثوقية وليس عجزًا فعليًا.", "القرار النهائي لصاحب الشركة."] :
            ["Figures are estimates built on the supplied training files; some files are modelled.", "We did not prove causal price elasticity: discounts did not raise volume in Retail and Online.", "There is no raw-material stock in the data, so we show requirement and reliability, not a physical shortage.", "The final decision stays with the owner."]).map((x) => <li key={x}>{x}</li>)}</ul></div></div></div>][i];
  }
  return <div className="brand-grad -m-4 min-h-[calc(100vh-4rem)] rounded-none p-6 text-white lg:-m-8 lg:p-12">
    <div className="mx-auto flex max-w-6xl flex-col" style={{ minHeight: "calc(100vh - 9rem)" }}>
      <div className="mb-8 flex flex-wrap items-center justify-between gap-3"><p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-brand-200">{i + 1} / {STEPS.length} · {STEPS[i][L]}</p>
        <div className="flex gap-1.5">{STEPS.map((s, n) => <button key={n} onClick={() => setI(n)} aria-label={s[L]} className={cn("h-1.5 rounded-full transition-all", n === i ? "w-8 bg-brand-500" : "w-3 bg-white/25 hover:bg-white/40")} />)}</div></div>
      <div className="flex-1">{body}</div>
      <div className="mt-10 flex items-center justify-between"><button onClick={() => go(-1)} disabled={i === 0} className="inline-flex items-center gap-2 rounded-xl border border-white/20 px-4 py-2 text-sm hover:bg-white/10 disabled:opacity-30"><Prev className="h-4 w-4" />{t("Back")}</button>
        <button onClick={() => go(1)} disabled={i === STEPS.length - 1} className="inline-flex items-center gap-2 rounded-xl bg-brand-500 px-5 py-2 text-sm font-medium text-ink-950 hover:bg-brand-200 disabled:opacity-30">{t("Next")}<Next className="h-4 w-4" /></button></div></div></div>;
}
