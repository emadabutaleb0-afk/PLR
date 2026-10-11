"use client";
/* eslint-disable @next/next/no-img-element */
import { cn } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";

export const BRAND = { name: "MERCHBRAIN", company: "El-Sharnouby for Clothing", tagline: "AI Commercial Decision & Profit Recovery Engine" };

/** The El Sharnouby emblem on a white disc, so the black artwork stays readable on dark and light surfaces. */
export function LogoBadge({ size = 40, className, ring = true }: { size?: number; className?: string; ring?: boolean }) {
  return <span className={cn("inline-grid shrink-0 place-items-center overflow-hidden rounded-full bg-white", ring && "ring-1 ring-black/10 shadow-[0_2px_10px_-2px_rgba(0,0,0,.35)]", className)} style={{ width: size, height: size }}>
    <img src="/brand/logo.png" alt="El Sharnouby for Clothing" width={size} height={size} className="h-full w-full object-contain p-[1.5px]" draggable={false} /></span>;
}

export function BrandLockup({ dark = false, size = 42, showTagline = true }: { dark?: boolean; size?: number; showTagline?: boolean }) {
  const { t } = useI18n();
  return <div className="flex items-center gap-3">
    <LogoBadge size={size} />
    <div className="min-w-0 leading-tight">
      <p className={cn("text-[15px] font-bold tracking-[0.18em]", dark ? "text-white" : "text-ink")}>{BRAND.name}</p>
      <p className={cn("text-[11px] font-medium", dark ? "text-brand-200/90" : "text-brand-700")}>{t(BRAND.company)}</p>
      {showTagline && <p className={cn("mt-0.5 hidden text-[10px] uppercase tracking-wider sm:block", dark ? "text-slate-400" : "text-slate-500")}>{t(BRAND.tagline)}</p>}
    </div></div>;
}
