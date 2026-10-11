"use client";
import { Languages } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";
/** One-click English <-> Arabic. Remembers the choice on this device. */
export function LangSwitch({ className }: { className?: string }) {
  const { lang, setLang } = useI18n();
  return <button type="button" onClick={() => setLang(lang === "ar" ? "en" : "ar")} aria-label="Language / اللغة"
    className={cn("inline-flex h-9 items-center gap-1.5 rounded-xl border border-slate-200 bg-surface px-3 text-sm font-medium text-slate-700 hover:bg-slate-50", className)}>
    <Languages className="h-4 w-4" />{lang === "ar" ? "English" : "العربية"}</button>;
}
