"use client";
import { useI18n } from "@/lib/i18n";
import { METHOD } from "@/lib/story";
import { Page } from "@/components/Page";
import { Badge, Card } from "@/components/ui/primitives";

export default function Method() {
  const { t, isAr } = useI18n(); const L = isAr ? "ar" : "en";
  const sec = (label: string, text: string) => <div><p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{t(label)}</p><p className="mt-0.5 text-sm text-slate-700">{text}</p></div>;
  return <Page title="How the numbers are calculated" sub="Every big number: what it means, how it is built, where it comes from and what it cannot tell you.">
    <div className="grid gap-4 lg:grid-cols-2">{METHOD.map((m) => <Card key={m.id} className="space-y-3 p-5">
      <div className="flex items-center justify-between gap-2"><h3 className="text-base font-semibold">{m.title[L]}</h3><Badge kind={m.basis}>{t(m.basis)}</Badge></div>
      {sec("What it is", m.what[L])}{sec("How it is calculated", m.how[L])}{sec("Data used", m.source[L])}
      <div className="rounded-xl bg-amber-50 p-3"><p className="text-[11px] font-semibold uppercase tracking-wide text-amber-700">{t("What it cannot tell you")}</p><p className="mt-0.5 text-sm text-amber-900">{m.limit[L]}</p></div></Card>)}</div>
    <p className="text-xs text-slate-500">{t("RECORDED = taken from the company files. ESTIMATE = calculated with a model or an assumption. EXPOSURE = money at stake, not a forecast of loss.")}</p>
  </Page>;
}
