"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApi } from "@/lib/hooks";
import { api } from "@/lib/api";
import { egp, pct } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { Page, Panel, Stat } from "@/components/Page";
import { ErrorState, LoadingBlock, LoadingGrid } from "@/components/States";
import { Badge, Button, Card } from "@/components/ui/primitives";

const PLAN_HINT: Record<string, string> = {
  max_profit: "Highest expected value; accepts more uncertainty.",
  balanced: "Penalises uncertain value and limits cash outlay.",
  min_risk: "Only decisions with confidence of at least 60%.",
};
const STATUS_KIND: Record<string, string> = { APPROVED: "INFO", EXECUTED: "WATCH", MEASURING: "WATCH", MEASURED: "OK", UNMEASURABLE: "LOW" };

function Plans() {
  const { t } = useI18n(); const qc = useQueryClient();
  const { data: d, error, isLoading, refetch } = useApi("/commercial/decision-plans");
  const [sel, setSel] = useState("balanced"); const [msg, setMsg] = useState<string | null>(null); const [stale, setStale] = useState(false);
  const approve = useMutation({
    mutationFn: () => api(`/commercial/decision-plans/${sel}/approve`, { method: "POST", body: JSON.stringify({ acknowledge_stale: stale }) }),
    onSuccess: (r: any) => { setMsg(t("{n} decisions approved and added to the Action Center; {s} skipped.", { n: r.approved, s: r.skipped })); setStale(false); qc.invalidateQueries(); },
    onError: (e: any) => { setMsg(e.message); setStale(e.status === 409); },
  });
  if (error) return <ErrorState error={error} retry={refetch} />;
  if (isLoading || !d) return <><LoadingGrid n={4} /><div className="mt-6"><LoadingBlock /></div></>;
  if (!d.plans?.length) return <Card className="p-6 text-sm text-slate-600">{d.note}</Card>;
  const p = d.plans.find((x: any) => x.name === sel) || d.plans[0]; const T = p.totals;
  return <div className="space-y-6">
    <div className="grid gap-3 md:grid-cols-3">{d.plans.map((x: any) => <button key={x.name} onClick={() => { setSel(x.name); setMsg(null); }} aria-pressed={sel === x.name}
      className={`rounded-2xl border p-4 text-start transition ${sel === x.name ? "border-brand-600 bg-brand-50 ring-1 ring-brand-600" : "border-slate-200 bg-surface hover:bg-slate-50"}`}>
      <p className="font-semibold">{t(x.label)}</p><p className="mt-1 text-xs text-slate-500">{t(PLAN_HINT[x.name] || x.description)}</p>
      <p className="mt-3 text-xl font-semibold">{egp(x.totals.risk_adjusted_value_egp)}</p><p className="text-xs text-slate-400">{t("confidence-adjusted value")} · {x.totals.decisions} {t("decisions")}</p></button>)}</div>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Stat label="Estimated value" value={egp(T.nominal_value_egp)} />
      <Stat label="Confidence-adjusted" value={egp(T.risk_adjusted_value_egp)} tone="text-emerald-600" />
      <Stat label="Value still uncertain" value={egp(T.value_at_risk_egp)} tone="text-amber-600" />
      <Stat label="Cash needed for purchases" value={egp(T.cash_outlay_egp)} /></div>
    <Card className="flex flex-wrap items-center justify-between gap-3 p-4">
      <p className="max-w-2xl text-sm text-slate-600">{t("Approving creates one action item per decision for its department. Nothing is executed automatically; marking an action In progress starts the measurement window.")}</p>
      <div className="flex items-center gap-3">{stale && <label className="flex items-center gap-2 text-xs text-amber-700"><input type="checkbox" checked={stale} onChange={(e) => setStale(e.target.checked)} />{t("Approve on old data (logged)")}</label>}
        <Button onClick={() => approve.mutate()} disabled={approve.isPending}>{t("Approve this plan")}</Button></div></Card>
    {msg && <p role="status" className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700">{msg}</p>}
    <Panel title="Decisions in this plan" hint="Ranked by confidence-adjusted value">
      <div className="overflow-auto"><table className="w-full text-sm"><thead className="text-xs uppercase text-slate-500"><tr><th className="py-2 text-start">{t("Decision")}</th><th className="text-start">{t("Department")}</th><th className="px-3 text-end">{t("Estimated value")}</th><th className="px-3 text-end">{t("Confidence")}</th><th className="px-3 text-end">{t("Cash")}</th></tr></thead>
        <tbody className="divide-y divide-slate-100">{p.decisions.map((x: any) => <tr key={x.rec_key}><td className="py-2 pe-3 font-medium">{x.title}</td><td>{t(x.department)}</td><td className="px-3 text-end">{egp(x.value_egp)}</td><td className="px-3 text-end">{pct(x.confidence, 0)}</td><td className="px-3 text-end">{x.cash_outlay_egp ? egp(x.cash_outlay_egp) : "—"}</td></tr>)}</tbody></table></div></Panel>
    <Panel title="Why other decisions were left out" hint={`${p.excluded_count} not chosen. Each one has a reason.`}>
      <details><summary className="cursor-pointer text-sm font-medium text-brand-700">{t("Show reasons")}</summary>
        <ul className="mt-3 divide-y divide-slate-100 text-sm">{p.excluded.map((x: any) => <li key={x.rec_key} className="py-2"><span className="font-medium">{x.title}</span> <span className="text-slate-400">({egp(x.value_egp)})</span><p className="text-xs text-slate-500">{x.reason}</p></li>)}</ul></details></Panel>
    <Panel title="Read this before you quote the numbers" hint="Basis and limits"><ul className="list-disc space-y-1.5 ps-5 text-sm text-slate-600">
      <li>{p.note}</li><li>{t("{c} candidate decisions, {k} real conflicts between them.", { c: d.candidates, k: d.conflicts })}</li>
      <li>{t("Each department can absorb at most {n} actions per plan. This is an assumption to confirm with management.", { n: d.settings.max_actions_per_department })}</li></ul></Panel>
  </div>;
}

function Tracking() {
  const { t } = useI18n(); const qc = useQueryClient();
  const { data: d, error, isLoading, refetch } = useApi("/decisions/tracking?page_size=100");
  const measure = useMutation({ mutationFn: () => api("/decisions/tracking/measure", { method: "POST" }), onSuccess: () => qc.invalidateQueries() });
  if (error) return <ErrorState error={error} retry={refetch} />;
  if (isLoading || !d) return <><LoadingGrid n={4} /><div className="mt-6"><LoadingBlock /></div></>;
  const s = d.summary;
  return <div className="space-y-6">
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
      <Stat label="Decisions tracked" value={s.decisions_tracked} /><Stat label="Waiting for execution" value={s.awaiting_execution} /><Stat label="Being measured" value={s.executed + s.measuring} />
      <Stat label="Measured" value={s.measured} /><Stat label="Claimable (EGP)" value={egp(s.claimable_gp_egp)} tone="text-emerald-600" /></div>
    <Card className="flex flex-wrap items-center justify-between gap-3 p-4"><p className="max-w-3xl text-xs text-slate-500">{s.note}</p>
      <Button variant="outline" onClick={() => measure.mutate()} disabled={measure.isPending}>{t("Measure now")}</Button></Card>
    <Panel title="Approved decisions" hint="Expected value and measured effect are always shown separately">
      {d.items.length === 0 ? <p className="text-sm text-slate-500">{t("Nothing approved yet. Approve a plan to start tracking.")}</p> :
        <div className="overflow-auto"><table className="w-full text-sm"><thead className="text-xs uppercase text-slate-500"><tr><th className="py-2 text-start">{t("Decision")}</th><th className="text-start">{t("Status")}</th><th className="text-end">{t("Expected (estimate)")}</th><th className="text-end">{t("Measured effect")}</th><th className="text-start">{t("Reading")}</th></tr></thead>
          <tbody className="divide-y divide-slate-100">{d.items.map((x: any) => <tr key={x.id}><td className="py-2 pe-3"><p className="font-medium">{String(x.category).replace(/_/g, " ").toLowerCase().replace(/^./, (c: string) => c.toUpperCase())} · {x.product_id || "—"}</p><p className="text-xs text-slate-400">{x.department} · {x.plan || t("single")}</p></td>
            <td><Badge kind={STATUS_KIND[x.status]}>{t(x.status)}</Badge></td><td className="text-end">{egp(x.expected_value_egp)}</td>
            <td className="text-end">{x.result?.effect_gp_egp !== undefined ? egp(x.result.effect_gp_egp) : "—"}</td>
            <td className="max-w-md text-xs text-slate-500">{x.result?.reading || x.result?.reason || t("Mark the action In progress to start measuring.")}</td></tr>)}</tbody></table></div>}</Panel></div>;
}

export default function Decisions() {
  const { t } = useI18n(); const [tab, setTab] = useState<"plans" | "tracking">("plans");
  return <Page title="Decision Plans" sub="Choose a consistent set of decisions across departments, approve it, then measure what happened.">
    <div role="tablist" className="flex gap-2">{(["plans", "tracking"] as const).map((k) => <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
      className={`rounded-xl px-4 py-2 text-sm font-medium ${tab === k ? "bg-accent text-accent-fg" : "bg-surface text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"}`}>{t(k === "plans" ? "Plans" : "Tracking & outcomes")}</button>)}</div>
    {tab === "plans" ? <Plans /> : <Tracking />}
  </Page>;
}
