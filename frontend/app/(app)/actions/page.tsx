"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import { egp } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { Page } from "@/components/Page";
import { DataTable, defaultQuery, qs } from "@/components/DataTable";
import { ErrorState } from "@/components/States";
import { Badge, Select } from "@/components/ui/primitives";
const STAT = ["NEW", "UNDER_REVIEW", "APPROVED", "IN_PROGRESS", "DONE", "REJECTED"]; const h = createColumnHelper<any>();
export default function Actions() {
  const { t } = useI18n(); const { can } = useAuth(); const qc = useQueryClient(); const [q, setQ] = useState(defaultQuery("created_at")); const [st, setSt] = useState("");
  const { data, error, isLoading, refetch } = useApi(`/actions?${qs(q, { status: st })}`);
  const m = useMutation({ mutationFn: (v: any) => api(`/actions/${v.id}`, { method: "PATCH", body: JSON.stringify({ status: v.status }) }), onSuccess: () => qc.invalidateQueries({ queryKey: [`/actions?${qs(q, { status: st })}`] }) });
  const cols = [h.accessor("title", { header: "Recommended action", cell: (i) => <div><p className="font-medium">{i.getValue()}</p><p className="text-xs text-slate-500">{i.row.original.recommended_action}</p></div> }), h.accessor("department", { header: "Department", cell: (i) => t(i.getValue()) }), h.accessor("owner_email", { header: "Owner" }),
    h.accessor("business_impact_egp", { header: "Business impact", cell: (i) => <span className="font-semibold text-emerald-600">{egp(i.getValue())}</span> }), h.accessor("urgency", { header: "Urgency", cell: (i) => <Badge kind={i.getValue()}>{t(i.getValue())}</Badge> }),
    h.accessor("status", { header: "Status", cell: (i) => can("decide") ? <Select value={i.getValue()} onChange={(e) => m.mutate({ id: i.row.original.id, status: e.target.value })} aria-label={t("Status")}>{STAT.map((s) => <option key={s} value={s}>{t(s)}</option>)}</Select> : <Badge>{t(i.getValue())}</Badge> })];
  if (error) return <ErrorState error={error} retry={refetch} />;
  return <Page title="Action Center" sub="Accepted recommendations become owned, trackable work." fresh={data?.freshness}>
    <div className="flex flex-wrap gap-2">{STAT.map((s) => <button key={s} onClick={() => { setSt(st === s ? "" : s); setQ({ ...q, page: 1 }); }} className={`rounded-xl border px-3 py-1.5 text-sm ${st === s ? "border-brand-500 bg-brand-50" : "border-slate-200 bg-surface"}`}>{t(s)} <b>{data?.counts?.[s] ?? 0}</b></button>)}</div>
    {m.error && <p className="text-sm text-rose-600">{(m.error as any).message}</p>}
    <DataTable columns={cols} data={data?.items || []} total={data?.total || 0} pages={data?.pages || 1} query={q} setQuery={setQ} loading={isLoading} empty="No actions yet — accept a recommendation to create one." /></Page>;
}
