"use client";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { Badge, Card } from "./ui/primitives";
import { egp, pct } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
export function KpiCard({ k, onClick }: { k: any; onClick?: () => void }) {
  const { t } = useI18n();
  if (!k) return null;
  const v = k.unit === "pct" ? pct(k.value) : k.unit === "x" ? `${k.value?.toFixed(1)}x` : egp(k.value);
  const up = (k.change ?? 0) >= 0;
  return <Card className="p-4" onClick={onClick}><p className="text-xs font-medium uppercase tracking-wide text-slate-500">{k.label}</p>
    <p className="mt-1.5 text-2xl font-semibold tracking-tight">{v}</p>
    {k.change !== null && k.change !== undefined && <p className={`mt-1 inline-flex items-center gap-1 text-xs font-medium ${up ? "text-emerald-600" : "text-rose-600"}`}>{up ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}{pct(Math.abs(k.change))} {t("vs previous period")}</p>}
    {k.note && <p className="mt-1 text-xs leading-snug text-slate-400">{k.note}</p>}</Card>;
}
export function DecisionCard({ d, onOpen }: { d: any; onOpen: (d: any) => void }) {
  const { t, isAr } = useI18n();
  return <Card className="flex flex-col gap-3 p-5 transition hover:-translate-y-0.5 hover:shadow-lg">
    <div className="flex items-center justify-between gap-2"><span className="text-xs font-semibold uppercase tracking-wide text-brand-600">{d.area}</span><Badge kind={d.urgency}>{t(d.urgency)}</Badge></div>
    <h3 className="font-semibold leading-snug">{d.title}</h3>
    <div className="space-y-2 text-sm"><p><span className="font-medium text-slate-500">{t("Problem")} · </span>{d.problem}</p>
      <p><span className="font-medium text-slate-500">{t("Why it matters")} · </span>{d.why?.[0]}</p>
      <p><span className="font-medium text-slate-500">{t("Do this")} · </span>{d.action}</p></div>
    <div className="mt-auto flex items-end justify-between border-t border-slate-100 pt-3"><div><p className="text-xs text-slate-500">{t("Expected impact (estimate)")}</p><p className="text-lg font-semibold text-emerald-600">{egp(d.estimated_value_egp)}</p></div>
      <div className="text-end"><p className="text-xs text-slate-500">{t("Confidence")}</p><p className="font-semibold">{Math.round(d.confidence * 100)}%</p></div></div>
    <button onClick={() => onOpen(d)} className="rounded-xl bg-accent px-3 py-2 text-sm font-medium text-accent-fg hover:bg-accent-hover">{t("Review & decide")} {isAr ? "←" : "→"}</button></Card>;
}
