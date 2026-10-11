"use client";
import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Database, FolderOpen, Loader2, PlayCircle } from "lucide-react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { Button, Card, Progress } from "./ui/primitives";
import { LoadingBlock } from "./States";
const OPEN = ["/data", "/users", "/account"];
const STAGE: Record<string, string> = { starting: "Starting", extract: "Reading files", validate: "Checking data quality", transform: "Cleaning", load: "Loading database", features: "Computing features", analytics: "Refreshing analytics", ml: "Updating models", recommendations: "Refreshing recommendations", done: "Done" };
/** Wraps every business page. If no data is loaded yet it shows a friendly "preparing your data" screen with live progress instead of an error. */
export function DataGate({ children }: { children: React.ReactNode }) {
  const { t } = useI18n(); const path = usePathname(); const qc = useQueryClient(); const wasEmpty = useRef(false);
  const st = useQuery({ queryKey: ["system-status"], queryFn: () => api("/system/status"), refetchInterval: (q) => (q.state.data && q.state.data.has_data && !q.state.data.importing ? false : 2000), retry: 1 });
  const start = useMutation({ mutationFn: () => api("/data/import", { method: "POST" }), onSuccess: () => st.refetch() });
  const d = st.data;
  useEffect(() => { if (d && !d.has_data) wasEmpty.current = true; if (d?.has_data && wasEmpty.current) { wasEmpty.current = false; qc.invalidateQueries(); } }, [d, qc]);
  if (OPEN.some((p) => path.startsWith(p))) return <>{children}</>;
  if (st.isLoading) return <LoadingBlock />;
  if (!d || d.has_data) return <>{children}</>;
  const pct = Math.round((d.progress || 0) * 100);
  return <div className="mx-auto mt-10 max-w-xl"><Card className="space-y-5 p-8 text-center">
    <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-brand-50 text-brand-600">{d.importing ? <Loader2 className="h-7 w-7 animate-spin" /> : d.data_folder_ok ? <Database className="h-7 w-7" /> : <FolderOpen className="h-7 w-7" />}</div>
    {d.importing ? <>
      <h2 className="text-xl font-semibold">{t("Preparing your data…")}</h2>
      <p className="text-sm text-slate-500">{t("The first load reads all company files, checks them and builds your decisions. It usually takes about a minute. You can keep this page open.")}</p>
      <div className="space-y-2"><div className="flex justify-between text-sm"><span className="font-medium">{t(STAGE[d.stage || "starting"] || "Starting")}</span><span>{pct}%</span></div><Progress value={d.progress || 0} /></div></>
    : d.data_folder_ok ? <>
      <h2 className="text-xl font-semibold">{t("Your company data is ready to load")}</h2>
      <p className="text-sm text-slate-500">{t("{n} company files were found. Load them once to build the dashboards and recommendations.", { n: d.files_found })}</p>
      {d.last_error && <p className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{d.last_error}</p>}
      {d.can_import ? <Button className="mx-auto" disabled={start.isPending} onClick={() => start.mutate()}><PlayCircle className="h-4 w-4" />{t("Load company data")}</Button> : <p className="text-sm text-slate-500">{t("Ask an administrator to load the company data.")}</p>}
      {start.error && <p className="text-sm text-rose-600">{(start.error as any).message}</p>}</>
    : <>
      <h2 className="text-xl font-semibold">{t("No company files found")}</h2>
      <p className="text-sm text-slate-500">{t("Copy the company CSV files into the folder data/private (next to the backend folder), then press Retry.")}</p>
      <Button variant="outline" className="mx-auto" onClick={() => st.refetch()}>{t("Retry")}</Button></>}
  </Card></div>;
}
