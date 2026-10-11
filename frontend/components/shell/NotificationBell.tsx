"use client";
import Link from "next/link";
import { Bell, ChevronRight, Inbox } from "lucide-react";
import { useApi } from "@/lib/hooks";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { Popover } from "../ui/popover";
import { Badge } from "../ui/primitives";
import { KIND_LABEL, KIND_ICON } from "../notify";

/** Bell with the REAL number of open work items from /workspace/notifications. No count is shown until the server answers. */
export function NotificationBell() {
  const { t } = useI18n(); const { user } = useAuth();
  const q = useApi(user ? "/workspace/notifications" : null, { refetchInterval: 120_000 });
  const n: number | null = q.data ? q.data.total : null;
  return <Popover label={t("Notifications")} trigger={({ open, toggle, ref, id }) =>
    <button ref={ref} onClick={toggle} aria-haspopup="true" aria-expanded={open} aria-controls={id} aria-label={n ? `${t("Notifications")}: ${n}` : t("Notifications")} className="relative grid h-9 w-9 place-items-center rounded-xl text-slate-600 hover:bg-sunken">
      <Bell className="h-[18px] w-[18px]" />{!!n && <span className="absolute -end-0.5 -top-0.5 min-w-[18px] rounded-full bg-rose-500 px-1 text-center text-[10px] font-semibold leading-[18px] text-white tabular">{n > 99 ? "99+" : n}</span>}</button>}>
    {(close) => <div>
      <div className="flex items-center justify-between px-3 py-2"><p className="text-sm font-semibold">{t("Notifications")}</p><Link href="/notifications" onClick={close} className="text-xs font-medium text-brand-600 hover:underline">{t("Open center")}</Link></div>
      {q.isLoading && <p className="px-3 py-6 text-center text-sm text-slate-500">{t("Loading…")}</p>}
      {q.isError && <p className="px-3 py-6 text-center text-sm text-rose-600" role="alert">{t("We could not load this")}</p>}
      {q.data && !q.data.items.length && <div className="px-3 py-8 text-center text-sm text-slate-500"><Inbox className="mx-auto mb-2 h-6 w-6 text-slate-300" />{t("Nothing needs your attention right now.")}</div>}
      {q.data && <ul className="max-h-[22rem] overflow-y-auto">{q.data.items.slice(0, 8).map((i: any) => { const Icon = KIND_ICON[i.kind] || Bell; return <li key={i.id}>
        <Link href={i.entity.url} onClick={close} className="flex items-start gap-3 rounded-xl px-3 py-2.5 hover:bg-sunken"><Icon className="mt-0.5 h-4 w-4 shrink-0 text-slate-500" />
          <span className="min-w-0 flex-1"><span className="block truncate text-sm font-medium">{i.title}</span><span className="block truncate text-xs text-slate-500">{t(KIND_LABEL[i.kind] || i.kind)}</span></span>
          <Badge kind={i.severity === "INFO" ? "INFO" : i.severity}>{t(i.severity)}</Badge><ChevronRight className="mt-1 h-4 w-4 text-slate-400 rtl:rotate-180" /></Link></li>; })}</ul>}
    </div>}</Popover>;
}
