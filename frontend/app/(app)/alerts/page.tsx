"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n";
import { Page } from "@/components/Page";
import { Empty, ErrorState, LoadingBlock } from "@/components/States";
import { Badge, Button, Card } from "@/components/ui/primitives";
export default function Alerts() {
  const { t } = useI18n(); const [sev, setSev] = useState(""); const qc = useQueryClient(); const path = `/alerts?page_size=100${sev ? `&severity=${sev}` : ""}`;
  const { data, error, isLoading, refetch } = useApi(path);
  const m = useMutation({ mutationFn: (v: any) => api(`/alerts/${v.id}`, { method: "PATCH", body: JSON.stringify({ status: v.status }) }), onSuccess: () => qc.invalidateQueries() });
  if (error) return <ErrorState error={error} retry={refetch} />;
  return <Page title="Alert Center" sub="Only what is important. Alerts are ranked by priority and capped to avoid noise." fresh={data?.freshness}>
    <div className="flex flex-wrap gap-2">{["", "CRITICAL", "WARNING", "OPPORTUNITY"].map((s) => <button key={s} onClick={() => setSev(s)} className={`rounded-xl border px-3 py-1.5 text-sm ${sev === s ? "border-brand-500 bg-brand-50" : "border-slate-200 bg-surface"}`}>{s ? t(s) : t("All")}</button>)}</div>
    {isLoading || !data ? <LoadingBlock /> : data.items.length === 0 ? <Empty title="No open alerts" hint="You are all caught up." /> : <div className="space-y-3">{data.items.map((a: any) =>
      <Card key={a.id} className={`flex flex-wrap items-center gap-3 p-4 ${a.status === "UNREAD" ? "border-s-4 border-s-brand-500" : "opacity-80"}`}><Badge kind={a.severity}>{t(a.severity)}</Badge>
        <div className="min-w-0 flex-1"><p className="font-medium">{a.title}</p><p className="text-sm text-slate-500">{a.body}</p></div>
        <div className="flex gap-2"><Button size="sm" variant="outline" disabled={m.isPending} onClick={() => m.mutate({ id: a.id, status: a.status === "UNREAD" ? "READ" : "UNREAD" })}>{a.status === "UNREAD" ? t("Mark read") : t("Mark unread")}</Button><Button size="sm" disabled={m.isPending} onClick={() => m.mutate({ id: a.id, status: "RESOLVED" })}>{t("Resolve")}</Button></div></Card>)}</div>}</Page>;
}
