"use client";
import { useState } from "react";
import { createColumnHelper } from "@tanstack/react-table";
import { useApi } from "@/lib/hooks";
import { egp } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { Page } from "@/components/Page";
import { DataTable, defaultQuery, qs } from "@/components/DataTable";
import { ErrorState } from "@/components/States";
import { Badge, Select } from "@/components/ui/primitives";
import { RecDialog } from "@/components/RecDialog";
const h = createColumnHelper<any>();
export default function Recovery() {
  const { t } = useI18n(); const [q, setQ] = useState(defaultQuery("priority_score")); const [urg, setUrg] = useState(""); const [open, setOpen] = useState<any>(null);
  const { data, error, isLoading, refetch } = useApi(`/recovery/priorities?${qs(q, { urgency: urg })}`);
  const cols = [h.accessor("priority_score", { header: "Score", cell: (i) => <span className="font-semibold">{i.getValue()}</span> }), h.accessor("title", { header: "Issue", cell: (i) => <button className="text-start font-medium text-brand-700 hover:underline" onClick={() => setOpen(i.row.original)}>{i.getValue()}</button> }),
    h.accessor("department", { header: "Department", cell: (i) => t(i.getValue()) }), h.accessor("urgency", { header: "Urgency", cell: (i) => <Badge kind={i.getValue()}>{t(i.getValue())}</Badge> }),
    h.accessor("estimated_loss_egp", { header: "Estimated loss", cell: (i) => egp(i.getValue()) }), h.accessor("estimated_value_egp", { header: "Recoverable", cell: (i) => <span className="font-semibold text-emerald-600">{egp(i.getValue())}</span> }),
    h.accessor("confidence", { header: "Confidence", cell: (i) => `${Math.round(i.getValue() * 100)}%` }), h.accessor("action", { header: "Recommended action", cell: (i) => <span className="text-slate-600">{i.getValue()}</span> })];
  if (error) return <ErrorState error={error} retry={refetch} />;
  return <Page title="Recovery Priorities" sub="One ranked list. The most valuable, most urgent, best-supported issues first." fresh={data?.freshness}>
    <DataTable columns={cols} data={data?.items || []} total={data?.total || 0} pages={data?.pages || 1} query={q} setQuery={setQ} loading={isLoading} exportPath="/export/recommendations?format=csv" exportName="recovery-priorities.csv"
      filters={<Select value={urg} onChange={(e) => { setUrg(e.target.value); setQ({ ...q, page: 1 }); }} aria-label={t("Urgency")}><option value="">{t("All urgency")}</option>{["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((u) => <option key={u} value={u}>{t(u)}</option>)}</Select>} />
    {data && <p className="text-sm text-slate-500">{t("Total recoverable (estimate)")}: <b className="text-emerald-600">{egp(data.total_value_egp)}</b> · {t("Total estimated loss exposure")}: <b>{egp(data.total_loss_egp)}</b></p>}
    {open && <RecDialog rec={open} onClose={() => setOpen(null)} />}</Page>;
}
