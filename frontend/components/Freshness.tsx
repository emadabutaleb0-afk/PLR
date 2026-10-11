"use client";
import { Badge } from "./ui/primitives";
import { Clock } from "lucide-react";
import { useI18n } from "@/lib/i18n";
export function Freshness({ f, dark }: { f?: any; dark?: boolean }) {
  const { t } = useI18n();
  if (!f) return null;
  const stale = f.status === "STALE" || f.status === "NO_DATA";
  return <div className={`flex flex-wrap items-center gap-2 text-xs ${dark ? "text-slate-300" : "text-slate-500"}`}><Clock className="h-3.5 w-3.5" /><span>{f.message}</span>{f.data_as_of && <span>· {t("data as of")} {f.data_as_of}</span>}{stale && <Badge kind="STALE">{t("Check before deciding")}</Badge>}</div>;
}
