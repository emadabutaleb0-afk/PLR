"use client";
/* eslint-disable @next/next/no-img-element */
import { cn } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";
import { useCompany } from "@/lib/company";

export const BRAND = { name: "BUSINESS GATE", company: "Business Gate", tagline: "Commercial Decision & Profit Intelligence" };

/** Modern Business Gate (BG) logo badge styled with Royal Indigo Linear theme */
export function LogoBadge({ size = 40, className, ring = true }: { size?: number; className?: string; ring?: boolean }) {
  return <span className={cn("inline-grid shrink-0 place-items-center overflow-hidden rounded-xl", ring && "shadow-[0_2px_12px_-2px_rgba(99,102,241,.38)]", className)} style={{ width: size, height: size }}>
    <img src="/brand/bg-logo.svg" alt="Business Gate" width={size} height={size} className="h-full w-full object-contain" draggable={false} />
  </span>;
}

export function BrandLockup({ dark = false, size = 42, showTagline = true }: { dark?: boolean; size?: number; showTagline?: boolean }) {
  const { t } = useI18n();
  const { companyName } = useCompany();
  return <div className="flex items-center gap-3">
    <LogoBadge size={size} />
    <div className="min-w-0 leading-tight">
      <p className={cn("text-[15px] font-bold tracking-[0.16em]", dark ? "text-white" : "text-ink")}>{BRAND.name}</p>
      <p className={cn("text-[11px] font-semibold truncate max-w-[180px]", dark ? "text-[#A5B4FC]" : "text-[#4F46E5]")}>{companyName || t(BRAND.company)}</p>
      {showTagline && <p className={cn("mt-0.5 hidden text-[10px] uppercase tracking-wider sm:block", dark ? "text-slate-400" : "text-slate-500")}>{t(BRAND.tagline)}</p>}
    </div></div>;
}
