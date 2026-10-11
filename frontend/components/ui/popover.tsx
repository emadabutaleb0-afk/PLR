"use client";
import { ReactNode, useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

/** Small anchored panel: closes on Escape and outside click, returns focus to its trigger. */
export function Popover({ trigger, children, label, className, align = "end" }: { trigger: (p: { open: boolean; toggle: () => void; ref: React.RefObject<HTMLButtonElement>; id: string }) => ReactNode; children: (close: () => void) => ReactNode; label: string; className?: string; align?: "start" | "end" }) {
  const [open, setOpen] = useState(false); const box = useRef<HTMLDivElement>(null); const btn = useRef<HTMLButtonElement>(null); const id = `pop-${label.replace(/\W+/g, "-").toLowerCase()}`;
  useEffect(() => {
    if (!open) return;
    const down = (e: MouseEvent) => { if (!box.current?.contains(e.target as Node)) setOpen(false); };
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") { setOpen(false); btn.current?.focus(); } };
    document.addEventListener("mousedown", down); document.addEventListener("keydown", key);
    return () => { document.removeEventListener("mousedown", down); document.removeEventListener("keydown", key); };
  }, [open]);
  return <div className="relative" ref={box}>{trigger({ open, toggle: () => setOpen((o) => !o), ref: btn, id })}
    {open && <div id={id} role="region" aria-label={label} className={cn("absolute top-full z-40 mt-2 w-[min(92vw,22rem)] animate-pop-in rounded-2xl border border-line bg-raised p-1.5 shadow-pop", align === "end" ? "end-0" : "start-0", className)}>{children(() => setOpen(false))}</div>}</div>;
}
