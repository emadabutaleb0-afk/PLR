"use client";
import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import { num, pct } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { Page, Panel } from "@/components/Page";
import { ErrorState, LoadingBlock } from "@/components/States";
import { Badge, Button, Card, Progress } from "@/components/ui/primitives";
const STAGE: Record<string, string> = { starting: "Starting", extract: "Reading files", validate: "Checking data quality", transform: "Cleaning", load: "Loading database", features: "Computing features", analytics: "Refreshing analytics", ml: "Updating models", recommendations: "Refreshing recommendations", done: "Done" };
export default function DataHealth() {
  const { t } = useI18n(); const { can } = useAuth(); const qc = useQueryClient(); const [jobId, setJobId] = useState<string | null>(null); const [msg, setMsg] = useState("");
  const { data: d, error, isLoading, refetch } = useApi("/data/health");
  const job = useApi(jobId ? `/jobs/${jobId}` : null, { refetchInterval: 1500 });
  const j = job.data; const running = !!j && ["QUEUED", "RUNNING"].includes(j.status);
  // when a job finishes: refresh every screen once (this used to run during render and could fire repeatedly)
  useEffect(() => { if (jobId && j && !running) { const id = setTimeout(() => { setJobId(null); qc.invalidateQueries(); }, 800); return () => clearTimeout(id); } }, [jobId, j, running, qc]);
  const start = useMutation({ mutationFn: (kind: string) => api(`/data/${kind}`, { method: "POST" }), onSuccess: (r) => { setMsg(""); setJobId(r.id); }, onError: (e: any) => setMsg(e.message) });
  if (error) return <ErrorState error={error} retry={refetch} />; if (isLoading || !d) return <LoadingBlock />;
  return <Page title="Data Health" sub="Is the data you are deciding on healthy and current?" fresh={d.freshness} right={<div className="flex gap-2">{can("data_import") && <Button disabled={running || start.isPending} onClick={() => start.mutate("import")}><RefreshCw className={`h-4 w-4 ${running ? "animate-spin" : ""}`} />{t("Refresh data")}</Button>}<Button variant="outline" disabled={running || start.isPending} onClick={() => start.mutate("validate")}>{t("Validate only")}</Button></div>}>
    {msg && <p className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700" role="alert">{msg}</p>}
    {j && <Card className="space-y-2 p-4"><div className="flex justify-between text-sm"><span className="font-medium">{j.kind === "import" ? t("Data refresh") : t("Validation")}: {running ? t(STAGE[j.stage] || "Starting") : t(j.status)}</span><span>{Math.round((j.progress || 0) * 100)}%</span></div><Progress value={j.progress || 0} />{j.message && <p className="text-sm text-rose-600">{j.message}</p>}</Card>}
    <div className="grid gap-4 md:grid-cols-4"><Card className="p-4"><p className="text-xs uppercase text-slate-500">{t("Overall")}</p><div className="mt-2"><Badge kind={d.overall}>{t(d.overall)}</Badge></div></Card>
      <Card className="p-4"><p className="text-xs uppercase text-slate-500">{t("Last data refresh")}</p><p className="mt-1 font-semibold">{d.last_refresh ? new Date(d.last_refresh.end_time || d.last_refresh.start_time).toLocaleString() : t("Never")}</p>{d.last_refresh && <p className="text-xs text-slate-500">{num(d.last_refresh.rows_loaded)} {t("rows loaded")} · {num(d.last_refresh.rows_rejected)} {t("rejected")}</p>}</Card>
      <Card className="p-4"><p className="text-xs uppercase text-slate-500">{t("Failed files")}</p><p className={`mt-1 text-2xl font-semibold ${d.failed_files.length ? "text-rose-600" : ""}`}>{d.failed_files.length}</p></Card>
      <Card className="p-4"><p className="text-xs uppercase text-slate-500">{t("Validation warnings")}</p><p className="mt-1 text-2xl font-semibold">{d.last_refresh?.validation_warnings ?? 0}</p></Card></div>
    {d.data_provenance.note && <Card className="flex gap-3 border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"><ShieldAlert className="h-5 w-5 shrink-0" /><p>{d.data_provenance.note} ({d.data_provenance.modeled_files.length} {t("files")})</p></Card>}
    {d.plausibility.filter((p: any) => p.status !== "OK").map((p: any) => <Card key={p.check} className="flex gap-3 border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"><ShieldAlert className="h-5 w-5 shrink-0" /><p>{p.message}</p></Card>)}
    <Panel title="Files"><div className="overflow-auto"><table className="w-full text-sm"><thead className="text-start text-xs uppercase text-slate-500"><tr>{["File", "Rows", "Last update", "Newest data", "Null rate", "Duplicate rate", "Status"].map((c) => <th key={c} className="py-2 text-start">{t(c)}</th>)}</tr></thead><tbody className="divide-y">{d.files.map((f: any) => <tr key={f.file}><td className="py-2 font-medium" dir="ltr">{f.file}{f.message && <p className="text-xs font-normal text-rose-600">{f.message}</p>}</td><td>{num(f.rows)}{f.rows_rejected > 0 && <span className="text-xs text-rose-600"> (+{f.rows_rejected} {t("rejected")})</span>}</td><td>{f.last_update ? new Date(f.last_update).toLocaleDateString() : "—"}</td><td>{f.newest_data_date || "—"}</td><td>{f.null_rate === null ? "—" : pct(f.null_rate, 2)}</td><td>{f.duplicate_rate === null ? "—" : pct(f.duplicate_rate, 2)}</td><td><Badge kind={f.status}>{t(f.status)}</Badge></td></tr>)}</tbody></table></div></Panel>
    {d.validation_warnings.length > 0 && <Panel title="Validation warnings & rejected rows" hint="Rejected rows are quarantined, never silently dropped"><ul className="space-y-1.5 text-sm">{d.validation_warnings.slice(0, 40).map((w: any, i: number) => <li key={i} className="flex gap-2"><Badge kind={w.severity === "reject" ? "CRITICAL" : "WARNING"}>{w.file}</Badge><span>{w.message}{w.rows ? ` — ${num(w.rows)} ${t("rows")}` : ""}{w.sample_rows?.length ? ` (${t("e.g. rows")} ${w.sample_rows.join(", ")})` : ""}</span></li>)}</ul></Panel>}
    {d.files_missing.length > 0 && <p className="text-sm text-slate-500">{t("Not found in the data folder")}: {d.files_missing.join(", ")}</p>}</Page>;
}
