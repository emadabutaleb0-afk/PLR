"use client";
import Link from "next/link";
import { useRef, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { ChevronRight, Inbox } from "lucide-react";
import { useApi } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import { Page } from "@/components/Page";
import { Badge, Card } from "@/components/ui/primitives";
import { ErrorState, LoadingBlock } from "@/components/States";
import { KIND_ICON, KIND_LABEL } from "@/components/notify";

const SEV_ORDER = ["CRITICAL", "WARNING", "OPPORTUNITY", "INFO"];
export default function Notifications() {
  const { t, lang } = useI18n(); const q = useApi<any>("/workspace/notifications", { refetchInterval: 120_000 }); const [kind, setKind] = useState("all"); const [sev, setSev] = useState("all"); const box = useRef<HTMLDivElement>(null);
  const items: any[] = (q.data?.items || []).filter((i: any) => (kind === "all" || i.kind === kind) && (sev === "all" || i.severity === sev));
  const v = useVirtualizer({ count: items.length, getScrollElement: () => box.current, estimateSize: () => 76, overscan: 8 });
  const when = (s?: string) => s ? new Date(s).toLocaleString(lang === "ar" ? "ar-EG-u-nu-latn" : "en-GB", { dateStyle: "medium", timeStyle: "short" }) : "";
  if (q.error) return <Page title="Notification Center"><ErrorState error={q.error} retry={q.refetch} /></Page>;
  const tot = q.data?.totals || {}; const kinds = Object.keys(KIND_LABEL).filter((k) => k in tot);
  return <Page title="Notification Center" sub="Everything that needs a person: approvals, alerts, data issues, delayed actions and finished measurements." fresh={q.data?.freshness}>
    {q.isLoading || !q.data ? <LoadingBlock h="h-80" /> : <>
      <div className="flex flex-wrap gap-2" role="group" aria-label={t("Filter by type")}>{[["all", "All", q.data.total], ...kinds.map((k) => [k, KIND_LABEL[k], tot[k]])].map(([k, l, n]: any) => <button key={k} aria-pressed={kind === k} onClick={() => setKind(k)} className={cn("rounded-full border px-3 py-1.5 text-xs font-medium", kind === k ? "border-accent bg-accent/10" : "border-line hover:bg-sunken")}>{t(l)} <span className="tabular text-slate-500">{n}</span></button>)}
        <label className="ms-auto text-xs text-slate-600">{t("Severity")} <select value={sev} onChange={(e) => setSev(e.target.value)} className="ms-1 h-8 rounded-lg border border-line bg-surface px-2 text-xs"><option value="all">{t("All")}</option>{SEV_ORDER.map((s) => <option key={s} value={s}>{t(s)}</option>)}</select></label></div>
      {!items.length ? <Card className="flex flex-col items-center gap-2 p-12 text-center"><Inbox className="h-8 w-8 text-slate-300" /><p className="font-medium">{t("Nothing needs your attention here.")}</p><p className="text-sm text-slate-500">{t("Counts come straight from the system. If a type is missing, your role does not see it.")}</p></Card>
        : <Card className="overflow-hidden"><div ref={box} className="max-h-[34rem] overflow-y-auto" role="list" aria-label={t("Notifications")}><div style={{ height: v.getTotalSize(), position: "relative" }}>{v.getVirtualItems().map((r) => { const i = items[r.index]; const Icon = KIND_ICON[i.kind] || KIND_ICON.default;
          return <div key={i.id} role="listitem" style={{ position: "absolute", insetInline: 0, top: 0, height: r.size, transform: `translateY(${r.start}px)` }} className="border-b border-line">
            <Link href={i.entity.url} className="flex h-full items-center gap-3 px-4 hover:bg-sunken"><Icon className="h-4 w-4 shrink-0 text-slate-500" /><span className="min-w-0 flex-1"><span dir="auto" className="block truncate text-sm font-medium">{i.title}</span><span dir="auto" className="block truncate text-xs text-slate-500">{i.detail}</span><span className="block text-[11px] text-slate-400">{t(KIND_LABEL[i.kind])}{i.ts ? ` · ${when(i.ts)}` : ""}</span></span>
              <Badge kind={i.severity === "INFO" ? "INFO" : i.severity}>{t(i.severity)}</Badge><ChevronRight className="h-4 w-4 shrink-0 text-slate-400 rtl:rotate-180" /></Link></div>; })}</div></div></Card>}
      <p className="text-xs text-slate-500">{t(q.data.note)} {t("Each list shows the most important items; the number on each type is the full count.")}</p></>}
  </Page>;
}
