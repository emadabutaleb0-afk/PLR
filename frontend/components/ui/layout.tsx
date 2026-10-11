"use client";
import { ReactNode, useCallback, useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";
import { Badge } from "./primitives";

/** Accessible tabs: roving focus with arrow keys (direction aware), Home/End, aria-selected. */
export function Tabs<T extends string>({ tabs, value, onChange, label }: { tabs: { key: T; label: string; count?: number | null }[]; value: T; onChange: (k: T) => void; label: string }) {
  const { t, dir } = useI18n(); const refs = useRef<Record<string, HTMLButtonElement | null>>({});
  const move = (i: number) => { const k = tabs[(i + tabs.length) % tabs.length].key; onChange(k); refs.current[k]?.focus(); };
  return <div role="tablist" aria-label={t(label)} className="flex gap-1 overflow-x-auto border-b border-line">
    {tabs.map((x, i) => <button key={x.key} ref={(el) => { refs.current[x.key] = el; }} role="tab" id={`tab-${x.key}`} aria-selected={value === x.key} aria-controls={value === x.key ? `panel-${x.key}` : undefined} tabIndex={value === x.key ? 0 : -1}
      onClick={() => onChange(x.key)}
      onKeyDown={(e) => { const fwd = dir === "rtl" ? "ArrowLeft" : "ArrowRight", back = dir === "rtl" ? "ArrowRight" : "ArrowLeft";
        if (e.key === fwd) { e.preventDefault(); move(i + 1); } else if (e.key === back) { e.preventDefault(); move(i - 1); } else if (e.key === "Home") { e.preventDefault(); move(0); } else if (e.key === "End") { e.preventDefault(); move(tabs.length - 1); } }}
      className={cn("-mb-px whitespace-nowrap border-b-2 px-3.5 py-2.5 text-sm font-medium transition-colors", value === x.key ? "border-accent text-slate-900" : "border-transparent text-slate-500 hover:text-slate-800")}>
      {t(x.label)}{x.count != null && <span className="ms-1.5 rounded-full bg-sunken px-1.5 py-0.5 text-[11px] tabular text-slate-600">{x.count}</span>}</button>)}</div>;
}
export const TabPanel = ({ id, active, children }: { id: string; active: boolean; children: ReactNode }) => active ? <div role="tabpanel" id={`panel-${id}`} aria-labelledby={`tab-${id}`} tabIndex={0} className="pt-4 outline-none">{children}</div> : null;

/** Two resizable panes. Drag the handle or focus it and use the arrow keys. Size is a percentage and can be saved in a workspace layout. */
export function SplitPane({ left, right, value, onChange, min = 22, max = 78, stackBelow = "lg", label }: { left: ReactNode; right: ReactNode; value: number; onChange: (v: number) => void; min?: number; max?: number; stackBelow?: "md" | "lg"; label: string }) {
  const { t, dir } = useI18n(); const box = useRef<HTMLDivElement>(null); const drag = useRef(false);
  const clamp = useCallback((v: number) => Math.min(max, Math.max(min, v)), [min, max]);
  const at = (clientX: number) => { const r = box.current!.getBoundingClientRect(); const p = ((dir === "rtl" ? r.right - clientX : clientX - r.left) / r.width) * 100; onChange(clamp(Math.round(p * 10) / 10)); };
  useEffect(() => { const mv = (e: PointerEvent) => drag.current && at(e.clientX); const up = () => { drag.current = false; document.body.style.userSelect = ""; };
    window.addEventListener("pointermove", mv); window.addEventListener("pointerup", up); return () => { window.removeEventListener("pointermove", mv); window.removeEventListener("pointerup", up); }; });
  const bp = stackBelow === "md" ? "md" : "lg";
  return <div ref={box} className={cn("flex flex-col gap-4", bp === "lg" ? "lg:flex-row lg:gap-0" : "md:flex-row md:gap-0")} style={{ ["--split" as any]: `${value}%` }}>
    <div className={cn("min-w-0", bp === "lg" ? "lg:w-[var(--split)] lg:pe-2" : "md:w-[var(--split)] md:pe-2")}>{left}</div>
    <div role="separator" aria-orientation="vertical" aria-label={t(label)} aria-valuemin={min} aria-valuemax={max} aria-valuenow={Math.round(value)} tabIndex={0}
      onPointerDown={(e) => { drag.current = true; document.body.style.userSelect = "none"; (e.target as HTMLElement).setPointerCapture?.(e.pointerId); }}
      onKeyDown={(e) => { const step = e.shiftKey ? 10 : 2; const grow = dir === "rtl" ? "ArrowLeft" : "ArrowRight", shrink = dir === "rtl" ? "ArrowRight" : "ArrowLeft";
        if (e.key === grow) { e.preventDefault(); onChange(clamp(value + step)); } else if (e.key === shrink) { e.preventDefault(); onChange(clamp(value - step)); } else if (e.key === "Home") onChange(min); else if (e.key === "End") onChange(max); }}
      className={cn("group relative hidden shrink-0 cursor-col-resize touch-none items-center justify-center px-1.5", bp === "lg" ? "lg:flex" : "md:flex")}><span className="h-16 w-1 rounded-full bg-line-strong transition group-hover:bg-accent group-focus-visible:bg-accent" /></div>
    <div className="min-w-0 flex-1 lg:ps-2">{right}</div></div>;
}

export type TimelineEvent = { ts: string; kind: string; actor?: string | null; text: string; comment?: string | null };
const DOT: Record<string, string> = { detected: "bg-slate-400", accept: "bg-emerald-500", approve: "bg-emerald-500", reject: "bg-rose-500", defer: "bg-amber-500", executed: "bg-sky-500", measured: "bg-brand-500", action_created: "bg-sky-500", audit: "bg-slate-300", outcome_entered: "bg-brand-500" };
/** Vertical activity list. Only events that exist in the backend are rendered. */
export function Timeline({ events, empty }: { events: TimelineEvent[]; empty?: string }) {
  const { t, lang } = useI18n();
  if (!events.length) return <p className="text-sm text-slate-500">{t(empty || "No recorded activity yet.")}</p>;
  const fmt = (s: string) => new Date(s).toLocaleString(lang === "ar" ? "ar-EG-u-nu-latn" : "en-GB", { dateStyle: "medium", timeStyle: "short" });
  return <ol className="relative space-y-4 border-s border-line ps-5">{events.map((e, i) => <li key={i} className="relative"><span className={cn("absolute -start-[25px] top-1.5 h-2.5 w-2.5 rounded-full ring-4 ring-surface", DOT[e.kind] || "bg-slate-400")} />
    <p className="text-sm font-medium">{e.text}</p><p className="text-xs text-slate-500 tabular">{fmt(e.ts)}{e.actor ? ` · ${e.actor}` : ""}</p>{e.comment && <p className="mt-1 rounded-lg bg-sunken p-2 text-sm text-slate-600">{e.comment}</p>}</li>)}</ol>;
}

/** Predicted vs realised value is always labelled: estimates are never shown as results. */
export const ValueTag = ({ kind }: { kind: "estimate" | "measured" | "recorded" }) => {
  const { t } = useI18n();
  return <Badge kind={kind === "measured" ? "READY" : kind === "estimate" ? "ESTIMATE" : "RECORDED"}>{t(kind === "measured" ? "Measured" : kind === "estimate" ? "Estimate" : "Recorded")}</Badge>;
};

/** Small dismissible feedback after a successful action; announced to screen readers. */
export function Toast({ message, onDone }: { message: string | null; onDone: () => void }) {
  useEffect(() => { if (!message) return; const id = setTimeout(onDone, 4500); return () => clearTimeout(id); }, [message, onDone]);
  return <div aria-live="polite" role="status" className="pointer-events-none fixed inset-x-0 bottom-4 z-[70] flex justify-center px-4">{message && <div className="pointer-events-auto animate-pop-in rounded-xl bg-ink-800 px-4 py-2.5 text-sm font-medium text-white shadow-pop">{message}</div>}</div>;
}
export const useToast = () => { const [m, setM] = useState<string | null>(null); return { message: m, show: setM, clear: useCallback(() => setM(null), []) }; };
