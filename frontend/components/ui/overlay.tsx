"use client";
import { ReactNode, useCallback, useEffect, useId, useRef } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import { Button } from "./primitives";

const FOCUSABLE = 'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

// Open modals, innermost last: only the top one reacts to keys, so Escape on a confirmation closes the confirmation and not the drawer under it.
const STACK: HTMLElement[] = [];

/** Modal behaviour shared by Drawer and ConfirmDialog: Escape closes, Tab stays inside, focus returns to the opener, page does not scroll behind. */
function useModal(open: boolean, onClose: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const opener = document.activeElement as HTMLElement | null;
    const prev = document.body.style.overflow; document.body.style.overflow = "hidden";
    const node = ref.current; if (node) STACK.push(node);
    const first = node?.querySelector<HTMLElement>("[data-autofocus]") || node?.querySelector<HTMLElement>(FOCUSABLE) || node; first?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (node && STACK[STACK.length - 1] !== node) return;
      if (e.key === "Escape") { e.stopPropagation(); onClose(); return; }
      if (e.key !== "Tab" || !node) return;
      const f = Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE)).filter((x) => x.offsetParent !== null);
      if (!f.length) { e.preventDefault(); return; }
      const a = f[0], z = f[f.length - 1];
      if (e.shiftKey && document.activeElement === a) { e.preventDefault(); z.focus(); } else if (!e.shiftKey && document.activeElement === z) { e.preventDefault(); a.focus(); }
    };
    document.addEventListener("keydown", onKey, true);
    return () => { const i = node ? STACK.indexOf(node) : -1; if (i >= 0) STACK.splice(i, 1); document.removeEventListener("keydown", onKey, true); document.body.style.overflow = prev; opener?.focus?.(); };
  }, [open, onClose]);
  return ref;
}

/** Contextual side drawer. Opens from the reading-direction end (right in English, left in Arabic). */
export function Drawer({ open, onClose, title, subtitle, children, footer, width = "max-w-xl" }: { open: boolean; onClose: () => void; title: ReactNode; subtitle?: ReactNode; children: ReactNode; footer?: ReactNode; width?: string }) {
  const { t } = useI18n(); const id = useId(); const stable = useCallback(onClose, [onClose]); const ref = useModal(open, stable);
  if (!open || typeof document === "undefined") return null;
  return createPortal(<div className="fixed inset-0 z-50" role="presentation">
    <div className="absolute inset-0 animate-fade-in bg-black/50" onClick={onClose} />
    <div ref={ref} role="dialog" aria-modal="true" aria-labelledby={id} tabIndex={-1} className={cn("absolute inset-y-0 end-0 flex w-full animate-slide-in-end flex-col border-s border-line bg-surface shadow-pop outline-none", width)}>
      <div className="flex items-start justify-between gap-3 border-b border-line px-5 py-4"><div className="min-w-0"><h2 id={id} className="truncate text-lg font-semibold">{title}</h2>{subtitle && <div className="mt-0.5 text-sm text-slate-500">{subtitle}</div>}</div>
        <button onClick={onClose} aria-label={t("Close")} className="rounded-lg p-1.5 text-slate-500 hover:bg-sunken"><X className="h-5 w-5" /></button></div>
      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">{children}</div>
      {footer && <div className="border-t border-line bg-sunken/60 px-5 py-3">{footer}</div>}
    </div></div>, document.body);
}

/** Confirmation before any consequential action. The primary button is never focused first, so Enter cannot approve by accident. */
export function ConfirmDialog({ open, onClose, onConfirm, title, children, confirmLabel, tone = "primary", busy, error }: { open: boolean; onClose: () => void; onConfirm: () => void; title: ReactNode; children: ReactNode; confirmLabel: string; tone?: "primary" | "danger" | "success"; busy?: boolean; error?: string | null }) {
  const { t } = useI18n(); const id = useId(); const stable = useCallback(onClose, [onClose]); const ref = useModal(open, stable);
  if (!open || typeof document === "undefined") return null;
  return createPortal(<div className="fixed inset-0 z-[60] grid place-items-center p-4" role="presentation">
    <div className="absolute inset-0 animate-fade-in bg-black/60" onClick={busy ? undefined : onClose} />
    <div ref={ref} role="alertdialog" aria-modal="true" aria-labelledby={id} tabIndex={-1} className="relative w-full max-w-md animate-pop-in rounded-2xl border border-line bg-surface p-5 shadow-pop outline-none">
      <h2 id={id} className="text-lg font-semibold">{title}</h2><div className="mt-2 space-y-2 text-sm text-slate-600">{children}</div>
      {error && <p role="alert" className="mt-3 rounded-lg bg-rose-50 p-2.5 text-sm text-rose-700">{error}</p>}
      <div className="mt-5 flex justify-end gap-2"><Button variant="outline" data-autofocus onClick={onClose} disabled={busy}>{t("Cancel")}</Button>
        <Button variant={tone} onClick={onConfirm} disabled={busy}>{busy ? t("Working…") : confirmLabel}</Button></div>
    </div></div>, document.body);
}
