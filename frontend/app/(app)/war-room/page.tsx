"use client";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { DndContext, DragEndEvent, DragOverlay, DragStartEvent, KeyboardSensor, PointerSensor, useDraggable, useDroppable, useSensor, useSensors } from "@dnd-kit/core";
import { GitCompare, GripVertical, Search } from "lucide-react";
import { useApi } from "@/lib/hooks";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { moveFor, useDecide } from "@/lib/decisions";
import { egp, pct } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Page } from "@/components/Page";
import { DecisionDrawer } from "@/components/decision/DecisionDrawer";
import { ConfirmDialog, Drawer } from "@/components/ui/overlay";
import { Toast, ValueTag, useToast } from "@/components/ui/layout";
import { Badge, Button, Input, Select } from "@/components/ui/primitives";
import { Empty, ErrorState, LoadingBlock } from "@/components/States";

type Card = any;
const LANE_HELP: Record<string, string> = { open: "Detected by the engines, waiting for a person.", deferred: "Put aside on purpose.", approved: "Approved; an action item exists but work has not started.", in_progress: "Someone is carrying it out.", measuring: "Executed; the result is measured once the after-window completes.", measured: "Result measured against comparable products.", rejected: "Closed without action." };
const URG_RING: Record<string, string> = { CRITICAL: "bg-rose-500", HIGH: "bg-orange-500", MEDIUM: "bg-amber-500", LOW: "bg-slate-400" };

function DecisionCard({ c, selected, onSelect, onOpen, draggable, compared, onCompare }: { c: Card; selected: boolean; onSelect: () => void; onOpen: () => void; draggable: boolean; compared: boolean; onCompare: () => void }) {
  const { t } = useI18n(); const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: c.rec_key, data: c, disabled: !draggable });
  return <li ref={setNodeRef} className={cn("rounded-xl border bg-surface p-3 shadow-card transition", selected ? "border-accent ring-1 ring-accent" : "border-line", isDragging && "opacity-40")}>
    <div className="flex items-start gap-2">
      {draggable && <button {...listeners} {...attributes} aria-label={`${t("Move")}: ${c.title}`} className="mt-0.5 cursor-grab touch-none rounded p-0.5 text-slate-400 hover:bg-sunken active:cursor-grabbing"><GripVertical className="h-4 w-4" /></button>}
      <button onClick={onOpen} className="min-w-0 flex-1 text-start"><span className="flex items-center gap-1.5"><span className={cn("h-2 w-2 shrink-0 rounded-full", URG_RING[c.urgency])} aria-hidden /><span className="line-clamp-2 text-sm font-medium">{c.title}</span></span>
        <span className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-500"><span className="font-semibold tabular text-slate-800">{egp(c.value_egp)}</span><ValueTag kind={c.measured ? "measured" : "estimate"} /><span className="tabular">{Math.round(c.confidence * 100)}%</span></span>
        <span className="mt-1 block truncate text-xs text-slate-500">{t(c.department)}{c.owner_email ? ` · ${c.owner_email}` : ""}{c.age_days != null && c.action_status !== "DONE" ? ` · ${c.age_days}d` : ""}</span></button>
      <input type="checkbox" checked={compared} onChange={onCompare} aria-label={`${t("Compare")}: ${c.title}`} className="mt-1 h-4 w-4 accent-brand-600" />
    </div></li>;
}
function Lane({ lane, children, activeDrag }: { lane: any; children: React.ReactNode; activeDrag: Card | null }) {
  const { t } = useI18n(); const { setNodeRef, isOver } = useDroppable({ id: lane.key });
  const ok = activeDrag ? !!moveFor(activeDrag, lane.key) || activeDrag.lane === lane.key : null;
  return <section ref={setNodeRef} aria-label={t(lane.label)} className={cn("flex w-[290px] shrink-0 flex-col rounded-2xl border bg-sunken/60 p-2.5 transition", isOver && ok && activeDrag?.lane !== lane.key ? "border-accent bg-accent/10" : "border-line", activeDrag && ok === false && "opacity-50")}>
    <header className="mb-2 px-1"><div className="flex items-center justify-between"><h2 className="text-sm font-semibold">{t(lane.label)}</h2><span className="rounded-full bg-surface px-2 text-xs font-semibold tabular">{lane.total}</span></div><p className="text-[11px] leading-snug text-slate-500">{t(LANE_HELP[lane.key])}</p></header>
    <ul className="min-h-[60px] flex-1 space-y-2 overflow-y-auto pe-0.5" style={{ maxHeight: "calc(100vh - 20rem)" }}>{children}</ul></section>;
}

function Board() {
  const { t } = useI18n(); const { can } = useAuth(); const router = useRouter(); const sp = useSearchParams(); const { feedback, patchAction } = useDecide(); const toast = useToast();
  const q = useApi<any>("/workspace/board");
  const [open, setOpen] = useState<string | null>(null); const [drag, setDrag] = useState<Card | null>(null); const [pending, setPending] = useState<{ card: Card; to: string; move: NonNullable<ReturnType<typeof moveFor>> } | null>(null);
  const [dept, setDept] = useState(""); const [urg, setUrg] = useState(""); const [text, setText] = useState(""); const [cmp, setCmp] = useState<string[]>([]); const [showCmp, setShowCmp] = useState(false); const [err, setErr] = useState<string | null>(null); const [ack, setAck] = useState(false); const [stale, setStale] = useState(false);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }), useSensor(KeyboardSensor));
  const allCards: Card[] = useMemo(() => (q.data?.lanes || []).flatMap((l: any) => l.cards), [q.data]);
  useEffect(() => { const k = sp.get("open"); const a = sp.get("action"); if (k) setOpen(k); else if (a && allCards.length) { const c = allCards.find((x) => String(x.action_id) === a); if (c) setOpen(c.rec_key); } }, [sp, allCards]);
  const departments = useMemo(() => Array.from(new Set(allCards.map((c) => c.department))).sort(), [allCards]);
  const keep = (c: Card) => (!dept || c.department === dept) && (!urg || c.urgency === urg) && (!text || `${c.title} ${c.product_id || ""} ${c.location_id || ""}`.toLowerCase().includes(text.toLowerCase()));
  const closeDrawer = () => { setOpen(null); if (sp.get("open") || sp.get("action")) router.replace("/war-room"); };
  const resetPending = () => { setPending(null); setErr(null); setAck(false); setStale(false); };
  const confirm = () => { if (!pending) return; const { card, move } = pending; const done = (m: string) => { toast.show(m); resetPending(); };
    const fail = (e: any) => { setErr(e.message); if (e.status === 409) setStale(true); };
    if (move.kind === "feedback") feedback.mutate({ key: card.rec_key, decision: move.decision, acknowledgeStale: ack }, { onSuccess: () => done(t(move.decision === "ACCEPT" ? "Approved. An action item was created." : move.decision === "DEFER" ? "Deferred." : "Rejected.")), onError: fail });
    else patchAction.mutate({ id: card.action_id, status: move.status }, { onSuccess: () => done(t(move.status === "DONE" ? "Marked as executed. Measurement window started." : "Marked as in progress.")), onError: fail }); };
  const end = (e: DragEndEvent) => { const c = drag; setDrag(null); const to = e.over?.id as string | undefined; if (!c || !to || to === c.lane) return;
    const m = moveFor(c, to); if (!m) { toast.show(t("That move is not a workflow step. Open the decision to see what can be done.")); return; }
    if (!can("decide")) { toast.show(t("Your role can view decisions but not change them.")); return; } setPending({ card: c, to, move: m }); };
  if (q.error) return <ErrorState error={q.error} retry={q.refetch} />;
  if (q.isLoading || !q.data) return <LoadingBlock h="h-[28rem]" />;
  const d = q.data; const compared = allCards.filter((c) => cmp.includes(c.rec_key));
  const labelOf = (k: string) => t(d.lanes.find((l: any) => l.key === k)?.label || k);
  return <>
    <div className="mb-4 flex flex-wrap items-end gap-3" role="search">
      <div className="relative min-w-[14rem] flex-1"><Search className="absolute start-3 top-3 h-4 w-4 text-slate-400" /><Input className="ps-9" value={text} onChange={(e) => setText(e.target.value)} placeholder={t("Filter by title, product or location")} aria-label={t("Filter decisions")} /></div>
      <Select value={dept} onChange={(e) => setDept(e.target.value)} aria-label={t("Department")}><option value="">{t("All departments")}</option>{departments.map((x) => <option key={x} value={x}>{t(x)}</option>)}</Select>
      <Select value={urg} onChange={(e) => setUrg(e.target.value)} aria-label={t("Urgency")}><option value="">{t("All urgencies")}</option>{["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((x) => <option key={x} value={x}>{t(x)}</option>)}</Select>
      <Button variant="outline" disabled={cmp.length < 2} onClick={() => setShowCmp(true)}><GitCompare className="h-4 w-4" />{t("Compare")} {cmp.length ? `(${cmp.length})` : ""}</Button></div>
    {!can("decide") && <p className="mb-3 rounded-xl bg-sunken p-3 text-sm text-slate-600">{t("Your role can review decisions but not approve them. Cards cannot be moved.")}</p>}
    <p className="mb-3 text-xs text-slate-500">{t("Dragging a card never approves or executes anything by itself: it opens a confirmation, and the server checks your role and the data freshness before recording it.")}</p>
    <DndContext sensors={sensors} onDragStart={(e: DragStartEvent) => setDrag(e.active.data.current as Card)} onDragEnd={end} onDragCancel={() => setDrag(null)}>
      <div className="-mx-1 flex gap-3 overflow-x-auto px-1 pb-3" tabIndex={0} aria-label={t("Decision lanes")}>
        {d.lanes.map((l: any) => { const cards = l.cards.filter(keep); return <Lane key={l.key} lane={l} activeDrag={drag}>
          {cards.map((c: Card) => <DecisionCard key={c.rec_key} c={c} selected={open === c.rec_key} onSelect={() => {}} onOpen={() => setOpen(c.rec_key)} draggable={d.can_decide && !!Object.keys(d.transitions).includes(l.key)} compared={cmp.includes(c.rec_key)} onCompare={() => setCmp((p) => p.includes(c.rec_key) ? p.filter((x) => x !== c.rec_key) : [...p, c.rec_key].slice(-3))} />)}
          {!cards.length && <li className="rounded-xl border border-dashed border-line p-4 text-center text-xs text-slate-500">{l.total ? t("No cards match the filters.") : t("Empty")}</li>}
          {l.total > l.cards.length && <li className="px-1 text-center text-[11px] text-slate-500">{t("Showing {n} of {total}. Use the filters or the Recovery Priorities page for the rest.", { n: l.cards.length, total: l.total })}</li>}</Lane>; })}
      </div>
      <DragOverlay>{drag ? <div className="w-[270px] rounded-xl border border-accent bg-surface p-3 shadow-pop"><p className="line-clamp-2 text-sm font-medium">{drag.title}</p><p className="mt-1 text-xs tabular">{egp(drag.value_egp)}</p></div> : null}</DragOverlay>
    </DndContext>
    <DecisionDrawer recKey={open} onClose={closeDrawer} onDone={toast.show} />
    <ConfirmDialog open={!!pending} onClose={resetPending} onConfirm={confirm} busy={feedback.isPending || patchAction.isPending} error={err} tone={pending?.move.kind === "feedback" && pending.move.decision === "REJECT" ? "danger" : "success"}
      confirmLabel={pending ? t(pending.move.kind === "feedback" ? { ACCEPT: "Approve", DEFER: "Defer", REJECT: "Reject" }[pending.move.decision] : pending.move.status === "DONE" ? "Mark as executed" : "Mark in progress") : ""} title={pending ? pending.card.title : ""}>
      {pending && <><p>{t("Move from")} <b>{labelOf(pending.card.lane)}</b> {t("to")} <b>{labelOf(pending.to)}</b>.</p>
        {pending.move.kind === "feedback" && pending.move.decision === "ACCEPT" && <p>{t("This approves the decision and creates an action item. People carry out the action; nothing runs automatically.")}</p>}
        {pending.move.kind === "action" && pending.move.status === "DONE" && <p>{t("Only confirm if the action was really carried out. This starts the before/after measurement.")}</p>}
        <p className="font-medium">{t("Expected impact")}: {egp(pending.card.value_egp, false)} ({t("estimate")})</p>
        {stale && <label className="flex items-start gap-2 rounded-lg bg-amber-50 p-2.5 text-amber-800"><input type="checkbox" className="mt-0.5" checked={ack} onChange={(e) => { setAck(e.target.checked); if (e.target.checked) setErr(null); }} /><span>{t("Approve anyway on old data. This is recorded in the audit log.")}</span></label>}</>}
    </ConfirmDialog>
    <Drawer open={showCmp} onClose={() => setShowCmp(false)} title={t("Compare decisions")} width="max-w-3xl">
      <div className="overflow-x-auto"><table className="w-full min-w-[32rem] text-sm"><thead><tr><th className="p-2 text-start text-xs font-medium text-slate-500" />{compared.map((c) => <th key={c.rec_key} scope="col" className="p-2 text-start align-top font-semibold">{c.title}</th>)}</tr></thead>
        <tbody className="divide-y divide-line">{[["Expected impact (estimate)", (c: Card) => egp(c.value_egp, false)], ["Confidence", (c: Card) => pct(c.confidence, 0)], ["Urgency", (c: Card) => t(c.urgency)], ["Department", (c: Card) => t(c.department)], ["Type", (c: Card) => c.category], ["Product", (c: Card) => c.product_id || "—"], ["Location", (c: Card) => c.location_id || "—"], ["Stage", (c: Card) => labelOf(c.lane)], ["Evidence available", (c: Card) => c.has_evidence ? t("Yes") : t("No")]].map(([l, f]: any) => <tr key={l}><th scope="row" className="p-2 text-start text-xs font-medium text-slate-500">{t(l)}</th>{compared.map((c) => <td key={c.rec_key} className="p-2 tabular">{f(c)}</td>)}</tr>)}</tbody></table></div>
      <p className="mt-3 text-xs text-slate-500">{t("Values are estimates. Two decisions that touch the same product, location or budget can conflict: the Decision Plans page checks conflicts, stock and budget together.")}</p>
    </Drawer>
    <Toast message={toast.message} onDone={toast.clear} />
  </>;
}
export default function WarRoom() {
  const { t } = useI18n(); const f = useApi<any>("/workspace/board");
  return <Page title="Decision War Room" sub="Review, compare and approve decisions. Every approval is confirmed, checked by the server and tracked until its result is measured." fresh={f.data?.freshness}><Suspense fallback={<LoadingBlock h="h-[28rem]" />}><Board /></Suspense></Page>;
}
