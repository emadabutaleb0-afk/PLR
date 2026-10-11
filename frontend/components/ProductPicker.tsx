"use client";
import { useEffect, useId, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { Input } from "./ui/primitives";

/** Type-ahead product selector backed by the permission-aware /search endpoint (a store manager only finds products in their own locations). */
export function ProductPicker({ value, label, onPick, placeholder }: { value: string | null; label?: string | null; onPick: (id: string | null, name?: string) => void; placeholder?: string }) {
  const { t } = useI18n(); const [q, setQ] = useState(""); const [res, setRes] = useState<any[]>([]); const [open, setOpen] = useState(false); const [i, setI] = useState(0); const box = useRef<HTMLDivElement>(null); const id = useId();
  useEffect(() => { if (q.trim().length < 2) { setRes([]); return; } let live = true; const h = setTimeout(() => api(`/search?q=${encodeURIComponent(q.trim())}`).then((x) => live && setRes((x.results || []).filter((r: any) => r.type === "Product"))).catch(() => live && setRes([])), 220); return () => { live = false; clearTimeout(h); }; }, [q]);
  useEffect(() => { const f = (e: MouseEvent) => { if (!box.current?.contains(e.target as Node)) setOpen(false); }; document.addEventListener("mousedown", f); return () => document.removeEventListener("mousedown", f); }, []);
  const pick = (r: any) => { onPick(r.id, r.label); setQ(""); setRes([]); setOpen(false); };
  if (value) return <div className="flex h-10 items-center gap-2 rounded-xl border border-line bg-surface px-3 text-sm"><span dir="auto" className="min-w-0 flex-1 truncate font-medium">{label || value}</span><span className="text-xs text-slate-500">{value}</span><button onClick={() => onPick(null)} aria-label={t("Clear selection")} className="rounded p-0.5 hover:bg-sunken"><X className="h-4 w-4" /></button></div>;
  return <div ref={box} className="relative"><Search className="absolute start-3 top-3 h-4 w-4 text-slate-400" />
    <Input role="combobox" aria-expanded={open && res.length > 0} aria-controls={id} aria-autocomplete="list" className="ps-9" value={q} placeholder={placeholder || t("Find a product by name or SKU")} onChange={(e) => { setQ(e.target.value); setOpen(true); setI(0); }} onFocus={() => setOpen(true)}
      onKeyDown={(e) => { if (e.key === "ArrowDown") { e.preventDefault(); setI((x) => Math.min(x + 1, res.length - 1)); } else if (e.key === "ArrowUp") { e.preventDefault(); setI((x) => Math.max(x - 1, 0)); } else if (e.key === "Enter" && res[i]) { e.preventDefault(); pick(res[i]); } else if (e.key === "Escape") setOpen(false); }} />
    {open && res.length > 0 && <ul id={id} role="listbox" className="absolute z-30 mt-1 max-h-72 w-full overflow-auto rounded-xl border border-line bg-raised p-1 shadow-pop">{res.map((r, k) => <li key={r.id} role="option" aria-selected={k === i}><button onMouseEnter={() => setI(k)} onClick={() => pick(r)} className={`flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-start text-sm ${k === i ? "bg-sunken" : ""}`}><span dir="auto" className="truncate font-medium">{r.label}</span><span className="text-xs text-slate-500">{r.sub}</span></button></li>)}</ul>}</div>;
}
