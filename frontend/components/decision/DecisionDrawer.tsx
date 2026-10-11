"use client";
import Link from "next/link";
import { useState } from "react";
import { Check, Clock, Ban, ExternalLink } from "lucide-react";
import { useApi } from "@/lib/hooks";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { useDecide, Verb } from "@/lib/decisions";
import { egp, pct } from "@/lib/format";
import { Drawer, ConfirmDialog } from "../ui/overlay";
import { Timeline, ValueTag } from "../ui/layout";
import { Badge, Button, Skeleton, Textarea } from "../ui/primitives";
import { Freshness } from "../Freshness";

const VERB: Record<Verb, { label: string; tone: "success" | "danger" | "primary"; text: string; icon: any }> = {
  ACCEPT: { label: "Approve", tone: "success", icon: Check, text: "This creates an action item for the owning department and starts tracking the expected result against a frozen baseline. Nothing is executed automatically: people carry out the action." },
  DEFER: { label: "Defer", tone: "primary", icon: Clock, text: "The decision stays on record as deferred and can be reopened later." },
  REJECT: { label: "Reject", tone: "danger", icon: Ban, text: "The decision is closed as rejected and will not create an action." },
};
export const Meter = ({ value, label }: { value: number; label: string }) => <div><div className="flex justify-between text-xs text-slate-500"><span>{label}</span><span className="tabular font-medium text-slate-800">{Math.round(value * 100)}%</span></div>
  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-sunken" role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(value * 100)}><div className="h-full rounded-full bg-accent" style={{ width: `${Math.round(value * 100)}%` }} /></div></div>;

/** Full decision detail: impact, risk and confidence, evidence, ownership, history, and the only place where a person approves, defers or rejects. */
export function DecisionDrawer({ recKey, onClose, onDone }: { recKey: string | null; onClose: () => void; onDone: (msg: string) => void }) {
  const { t } = useI18n(); const { can } = useAuth(); const { feedback } = useDecide();
  const rec = useApi<any>(recKey ? `/recommendations/${encodeURIComponent(recKey).replace(/%3A/g, ":")}` : null);
  const hist = useApi<any>(recKey ? `/workspace/decisions/history?rec_key=${encodeURIComponent(recKey)}` : null);
  const [verb, setVerb] = useState<Verb | null>(null); const [comment, setComment] = useState(""); const [ack, setAck] = useState(false); const [stale, setStale] = useState(false); const [err, setErr] = useState<string | null>(null);
  const d = rec.data; const ev = d?.evidence || {}; const canAct = can("decide") && d && ["OPEN", "DEFERRED"].includes(d.status);
  const close = () => { setVerb(null); setComment(""); setAck(false); setStale(false); setErr(null); };
  const submit = () => verb && recKey && feedback.mutate({ key: recKey, decision: verb, comment, acknowledgeStale: ack }, {
    onSuccess: () => { onDone(t(verb === "ACCEPT" ? "Approved. An action item was created." : verb === "DEFER" ? "Deferred." : "Rejected.")); close(); },
    onError: (e: any) => { setErr(e.message); if (e.status === 409) setStale(true); } });
  return <><Drawer open={!!recKey} onClose={onClose} width="max-w-2xl" title={d?.title || t("Decision")} subtitle={d && <span className="flex flex-wrap items-center gap-2"><Badge kind={d.urgency}>{t(d.urgency)}</Badge><Badge kind={d.status === "ACCEPTED" ? "DONE" : d.status === "REJECTED" ? "FAILED" : d.status === "DEFERRED" ? "WATCH" : "NEW"}>{t(d.status)}</Badge><span>{t(d.department)}</span></span>}
    footer={canAct ? <div className="flex flex-wrap gap-2">{(Object.keys(VERB) as Verb[]).filter((v) => !(v === "DEFER" && d.status === "DEFERRED")).map((v) => { const I = VERB[v].icon; return <Button key={v} variant={v === "ACCEPT" ? "success" : "outline"} onClick={() => setVerb(v)}><I className="h-4 w-4" />{t(VERB[v].label)}</Button>; })}</div>
      : d ? <p className="text-xs text-slate-500">{can("decide") ? t("This decision is already closed or in progress.") : t("Your role can view this decision but not approve it.")}</p> : null}>
    {rec.isLoading && <div className="space-y-3"><Skeleton className="h-24" /><Skeleton className="h-40" /></div>}
    {rec.isError && <p role="alert" className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{(rec.error as any)?.message}</p>}
    {d && <div className="space-y-5 text-sm">
      <section><h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{t("What happened")}</h3><p>{d.problem}</p></section>
      <section className="rounded-xl border border-accent/30 bg-accent/10 p-4"><h3 className="text-xs font-semibold uppercase tracking-wide text-slate-600">{t("Recommended action")}</h3><p className="mt-1 text-base font-medium">{d.action}</p></section>
      <section className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl bg-sunken p-3"><div className="flex items-center justify-between"><p className="text-xs text-slate-500">{t("Expected impact")}</p><ValueTag kind={d.is_estimate ? "estimate" : "recorded"} /></div><p className="mt-1 text-lg font-semibold tabular">{egp(d.estimated_value_egp, false)}</p><p className="text-xs text-slate-500">{t(d.impact_type?.replace(/_/g, " "))}</p></div>
        <div className="rounded-xl bg-sunken p-3"><Meter value={d.confidence} label={t("Confidence")} /></div>
        <div className="rounded-xl bg-sunken p-3"><p className="text-xs text-slate-500">{t("Downside if nothing is done")}</p><p className="mt-1 text-lg font-semibold tabular">{d.estimated_loss_egp ? egp(d.estimated_loss_egp, false) : "—"}</p></div></section>
      <section><h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{t("Evidence")}</h3><ul className="list-disc space-y-1 ps-5">{d.why?.map((w: string, i: number) => <li key={i}>{w}</li>)}</ul>
        {ev.basis && <p className="mt-2 text-xs text-slate-500">{t("Basis")}: {ev.basis}</p>}{ev.assumption && <p className="mt-1 text-xs text-amber-700">{t("Assumption")}: {ev.assumption}</p>}
        {d.is_estimate && <p className="mt-2 text-xs text-slate-500">{t("This is an estimate derived from your data, not a realised result.")}</p>}</section>
      <section className="flex flex-wrap gap-2">{d.product_id && <Link href={`/products/${d.product_id}`} className="inline-flex items-center gap-1 rounded-lg border border-line px-2.5 py-1 text-xs font-medium hover:bg-sunken"><ExternalLink className="h-3 w-3" />{t("Product 360")} · {d.product_id}</Link>}
        {d.product_id && <Link href={`/investigate?product=${d.product_id}`} className="rounded-lg border border-line px-2.5 py-1 text-xs font-medium hover:bg-sunken">{t("Investigate")}</Link>}
        {d.product_id && <Link href={`/map?focus=${d.product_id}`} className="rounded-lg border border-line px-2.5 py-1 text-xs font-medium hover:bg-sunken">{t("Show on map")}</Link>}</section>
      {d.tracking && <section className="rounded-xl border border-line p-3"><h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t("Tracking")}</h3><p className="mt-1">{t(d.tracking.status)} · {t("expected")} {egp(d.tracking.expected_value_egp, false)} ({t("estimate")})</p>
        {d.tracking.status === "MEASURED" && d.tracking.result?.effect_gp_egp != null && <p className="mt-1">{t("Measured effect on gross profit")}: <b className="tabular">{egp(d.tracking.result.effect_gp_egp, false)}</b> · {d.tracking.result.significant ? t("stands out from placebo tests") : t("not distinguishable from chance, nothing is claimed")}</p>}
        {d.tracking.result?.reason && <p className="mt-1 text-xs text-slate-500">{d.tracking.result.reason}</p>}</section>}
      {d.status === "ACCEPTED" && <p className="text-xs text-slate-500">{t("Owners and execution status are managed on the action item in the Action Center.")} <Link href="/actions" className="font-medium text-brand-600 hover:underline">{t("Open Action Center")}</Link></p>}
      <section><h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">{t("Activity history")}</h3>{hist.isLoading ? <Skeleton className="h-20" /> : <Timeline events={hist.data?.events || []} />}</section>
      <Freshness f={d.freshness} />
    </div>}
  </Drawer>
  <ConfirmDialog open={!!verb} onClose={close} onConfirm={submit} busy={feedback.isPending} error={err} tone={verb ? VERB[verb].tone : "primary"} confirmLabel={verb ? t(VERB[verb].label) : ""} title={verb ? `${t(VERB[verb].label)}: ${d?.title ?? ""}` : ""}>
    {verb && <><p>{t(VERB[verb].text)}</p>{verb === "ACCEPT" && d && <p className="font-medium">{t("Expected impact")}: {egp(d.estimated_value_egp, false)} ({t("estimate")})</p>}
      <label className="block"><span className="sr-only">{t("Comment")}</span><Textarea rows={2} value={comment} onChange={(e) => setComment(e.target.value)} placeholder={t("Add a comment (optional)")} /></label>
      {stale && <label className="flex items-start gap-2 rounded-lg bg-amber-50 p-2.5 text-amber-800"><input type="checkbox" className="mt-0.5" checked={ack} onChange={(e) => { setAck(e.target.checked); if (e.target.checked) setErr(null); }} /><span>{t("Approve anyway on old data. This is recorded in the audit log.")}</span></label>}</>}
  </ConfirmDialog></>;
}
