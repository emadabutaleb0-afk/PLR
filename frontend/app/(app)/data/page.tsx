"use client";
import { useEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Building, FileUp, RefreshCw, ShieldAlert, UploadCloud, X } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useCompany } from "@/lib/company";
import { useApi } from "@/lib/hooks";
import { num, pct } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { Page, Panel } from "@/components/Page";
import { ErrorState, LoadingBlock } from "@/components/States";
import { Badge, Button, Card, Input, Progress } from "@/components/ui/primitives";
import { cn } from "@/lib/utils";

const STAGE: Record<string, string> = {
  starting: "Starting",
  extract: "Reading files",
  validate: "Checking data quality",
  transform: "Cleaning",
  load: "Loading database",
  features: "Computing features",
  analytics: "Refreshing analytics",
  ml: "Updating models",
  recommendations: "Refreshing recommendations",
  done: "Done",
};

export default function DataHealth() {
  const { t } = useI18n();
  const { can } = useAuth();
  const { companyName, source: companySource, setCompanyName, refreshCompany } = useCompany();
  const qc = useQueryClient();
  const [jobId, setJobId] = useState<string | null>(null);
  const [msg, setMsg] = useState("");
  const [companyInput, setCompanyInput] = useState(companyName);
  const [companyMsg, setCompanyMsg] = useState("");
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    setCompanyInput(companyName);
  }, [companyName]);

  const { data: d, error, isLoading, refetch } = useApi("/data/health");
  const job = useApi(jobId ? `/jobs/${jobId}` : null, { refetchInterval: 1500 });
  const j = job.data;
  const running = !!j && ["QUEUED", "RUNNING"].includes(j.status);

  useEffect(() => {
    if (jobId && j && !running) {
      const id = setTimeout(() => {
        setJobId(null);
        qc.invalidateQueries();
        refreshCompany();
      }, 800);
      return () => clearTimeout(id);
    }
  }, [jobId, j, running, qc, refreshCompany]);

  const start = useMutation({
    mutationFn: (kind: string) => api(`/data/${kind}`, { method: "POST" }),
    onSuccess: (r) => {
      setMsg("");
      setJobId(r.id);
    },
    onError: (e: any) => setMsg(e.message),
  });

  const handleSaveCompany = async () => {
    try {
      setCompanyMsg("");
      await setCompanyName(companyInput);
      setCompanyMsg(t("Company name updated successfully."));
      setTimeout(() => setCompanyMsg(""), 3500);
    } catch (e: any) {
      setCompanyMsg(e.message || t("Failed to update company name."));
    }
  };

  const handleResetCompany = async () => {
    try {
      setCompanyMsg("");
      await setCompanyName("");
      setCompanyMsg(t("Reverted to automatic detection."));
      setTimeout(() => setCompanyMsg(""), 3500);
    } catch (e: any) {
      setCompanyMsg(e.message || t("Failed to reset company name."));
    }
  };

  const addFiles = (files: File[]) => {
    const csvs = files.filter((f) => f.name.toLowerCase().endsWith(".csv"));
    if (csvs.length > 0) {
      setUploadFiles((prev) => {
        const existingNames = new Set(prev.map((p) => p.name));
        const newOnes = csvs.filter((f) => !existingNames.has(f.name));
        return [...prev, ...newOnes];
      });
      setUploadMsg("");
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      addFiles(Array.from(e.target.files));
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      addFiles(Array.from(e.dataTransfer.files));
    }
  };

  const removeFile = (idx: number) => {
    setUploadFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const clearAllFiles = () => {
    setUploadFiles([]);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleUpload = async (autoRefresh = true) => {
    if (!uploadFiles.length) return;
    setUploading(true);
    setUploadMsg("");
    try {
      const fd = new FormData();
      uploadFiles.forEach((f) => fd.append("files", f));
      const res = await api(`/data/upload?auto_refresh=${autoRefresh}`, {
        method: "POST",
        body: fd,
      });
      setUploadFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = "";
      if (res?.job?.id) {
        setJobId(res.job.id);
      } else {
        qc.invalidateQueries();
        refetch();
        refreshCompany();
      }
      setUploadMsg(t("{n} file(s) uploaded successfully.", { n: res.total_saved }));
    } catch (e: any) {
      setUploadMsg(e.message || t("Upload failed."));
    } finally {
      setUploading(false);
    }
  };

  if (error) return <ErrorState error={error} retry={refetch} />;
  if (isLoading || !d) return <LoadingBlock />;

  return (
    <Page
      title="Data Health"
      sub="Manage data tables, upload new files, and configure target company name"
      fresh={d.freshness}
      right={
        <div className="flex flex-wrap gap-2">
          {can("data_import") && (
            <Button
              disabled={running || start.isPending}
              loading={running || start.isPending}
              onClick={() => start.mutate("import")}
            >
              {!running && !start.isPending && <RefreshCw className="h-4 w-4" />}
              {t("Refresh data")}
            </Button>
          )}
          <Button
            variant="outline"
            disabled={running || start.isPending}
            onClick={() => start.mutate("validate")}
          >
            {t("Validate only")}
          </Button>
        </div>
      }
    >
      {msg && <p className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700" role="alert">{msg}</p>}

      {j && (
        <Card className="space-y-2 p-4">
          <div className="flex justify-between text-sm">
            <span className="font-medium">
              {j.kind === "import" ? t("Data refresh") : t("Validation")}: {running ? t(STAGE[j.stage] || "Starting") : t(j.status)}
            </span>
            <span>{Math.round((j.progress || 0) * 100)}%</span>
          </div>
          <Progress value={j.progress || 0} />
          {j.message && <p className="text-sm text-rose-600">{j.message}</p>}
        </Card>
      )}

      {/* Target Company Name Configuration */}
      <Card className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Building className="h-5 w-5 text-accent" />
              <h3 className="font-semibold text-slate-900">{t("Target Company Name")}</h3>
              <Badge kind={companySource === "user" ? "HEALTHY" : "NEUTRAL"}>
                {companySource === "user" ? t("Custom") : companySource === "data" ? t("Detected from data") : t("Default")}
              </Badge>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              {t("Dynamically displayed across all dashboards, question headers, and weekly executive reports.")}
            </p>
          </div>
          <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
            <Input
              value={companyInput}
              onChange={(e) => setCompanyInput(e.target.value)}
              placeholder="e.g. Gulf Foods Trading"
              className="w-full sm:w-64"
            />
            <Button onClick={handleSaveCompany} size="sm">
              {t("Save")}
            </Button>
            {companySource === "user" && (
              <Button variant="outline" onClick={handleResetCompany} size="sm">
                {t("Auto-Detect")}
              </Button>
            )}
          </div>
        </div>
        {companyMsg && <p className="mt-2 text-xs font-medium text-emerald-600">{companyMsg}</p>}
      </Card>

      {/* Direct File Upload & Ingestion Guide with Drag-and-Drop */}
      <Card
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          "space-y-4 border-2 border-dashed p-5 transition-colors",
          isDragging
            ? "border-accent bg-accent/10"
            : "border-line bg-surface hover:border-line-strong"
        )}
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <UploadCloud className="h-5 w-5 text-accent" />
              <h3 className="font-semibold text-slate-900">{t("Upload Data Tables (CSV)")}</h3>
            </div>
            <p className="text-xs text-slate-600">
              {t("Drag & drop CSV files here, or")}{" "}
              {t("Upload company CSV files here, or copy them directly into the folder")}{" "}
              <code className="rounded bg-sunken border border-line px-1 py-0.5 text-xs text-slate-800">
                data/private/
              </code>
              .
            </p>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              multiple
              accept=".csv"
              className="hidden"
              id="csv-file-input"
            />
            <Button
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              <FileUp className="h-4 w-4" />
              {t("Select CSV files")}
            </Button>
            <Button
              onClick={() => handleUpload(true)}
              disabled={uploading || !uploadFiles.length}
              loading={uploading}
            >
              {!uploading && <RefreshCw className="h-4 w-4" />}
              {t("Upload & Refresh Data")}
            </Button>
          </div>
        </div>

        {uploadFiles.length > 0 && (
          <div className="rounded-xl border border-line bg-sunken p-3 text-xs">
            <div className="flex items-center justify-between">
              <p className="font-medium text-slate-800">
                {t("Files ready for upload:")} {uploadFiles.length}
              </p>
              <button
                type="button"
                onClick={clearAllFiles}
                className="text-xs text-slate-500 hover:text-rose-600 underline"
              >
                {t("Clear files")}
              </button>
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {uploadFiles.map((f, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1.5 rounded-md border border-line bg-surface px-2 py-0.5 text-[11px] text-slate-700"
                >
                  <span>
                    {f.name} ({(f.size / 1024).toFixed(0)} KB)
                  </span>
                  <button
                    type="button"
                    onClick={() => removeFile(i)}
                    aria-label={`Remove ${f.name}`}
                    className="text-slate-400 hover:text-rose-600"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          </div>
        )}
        {uploadMsg && <p className="text-xs font-medium text-emerald-600">{uploadMsg}</p>}
      </Card>

      <div className="grid gap-4 md:grid-cols-4">
        <Card className="p-4">
          <p className="text-xs uppercase text-slate-500">{t("Overall")}</p>
          <div className="mt-2"><Badge kind={d.overall}>{t(d.overall)}</Badge></div>
        </Card>
        <Card className="p-4">
          <p className="text-xs uppercase text-slate-500">{t("Last data refresh")}</p>
          <p className="mt-1 font-semibold">{d.last_refresh ? new Date(d.last_refresh.end_time || d.last_refresh.start_time).toLocaleString() : t("Never")}</p>
          {d.last_refresh && (
            <p className="text-xs text-slate-500">
              {num(d.last_refresh.rows_loaded)} {t("rows loaded")} · {num(d.last_refresh.rows_rejected)} {t("rejected")}
            </p>
          )}
        </Card>
        <Card className="p-4">
          <p className="text-xs uppercase text-slate-500">{t("Failed files")}</p>
          <p className={`mt-1 text-2xl font-semibold ${d.failed_files.length ? "text-rose-600" : ""}`}>{d.failed_files.length}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs uppercase text-slate-500">{t("Validation warnings")}</p>
          <p className="mt-1 text-2xl font-semibold">{d.last_refresh?.validation_warnings ?? 0}</p>
        </Card>
      </div>

      {d.data_provenance.note && (
        <Card className="flex gap-3 border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <ShieldAlert className="h-5 w-5 shrink-0" />
          <p>{d.data_provenance.note} ({d.data_provenance.modeled_files.length} {t("files")})</p>
        </Card>
      )}

      {d.plausibility.filter((p: any) => p.status !== "OK").map((p: any) => (
        <Card key={p.check} className="flex gap-3 border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <ShieldAlert className="h-5 w-5 shrink-0" />
          <p>{p.message}</p>
        </Card>
      ))}

      <Panel title="Files">
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead className="text-start text-xs uppercase text-slate-500">
              <tr>
                {["File", "Rows", "Last update", "Newest data", "Null rate", "Duplicate rate", "Status"].map((c) => (
                  <th key={c} className="py-2 text-start">{t(c)}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {d.files.map((f: any) => (
                <tr key={f.file}>
                  <td className="py-2 font-medium" dir="ltr">
                    {f.file}
                    {f.message && <p className="text-xs font-normal text-rose-600">{f.message}</p>}
                  </td>
                  <td>{num(f.rows)}{f.rows_rejected > 0 && <span className="text-xs text-rose-600"> (+{f.rows_rejected} {t("rejected")})</span>}</td>
                  <td>{f.last_update ? new Date(f.last_update).toLocaleDateString() : "—"}</td>
                  <td>{f.newest_data_date || "—"}</td>
                  <td>{f.null_rate === null ? "—" : pct(f.null_rate, 2)}</td>
                  <td>{f.duplicate_rate === null ? "—" : pct(f.duplicate_rate, 2)}</td>
                  <td><Badge kind={f.status}>{t(f.status)}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {d.validation_warnings.length > 0 && (
        <Panel title="Validation warnings & rejected rows" hint="Rejected rows are quarantined, never silently dropped">
          <ul className="space-y-1.5 text-sm">
            {d.validation_warnings.slice(0, 40).map((w: any, i: number) => (
              <li key={i} className="flex gap-2">
                <Badge kind={w.severity === "reject" ? "CRITICAL" : "WARNING"}>{w.file}</Badge>
                <span>
                  {w.message}
                  {w.rows ? ` — ${num(w.rows)} ${t("rows")}` : ""}
                  {w.sample_rows?.length ? ` (${t("e.g. rows")} ${w.sample_rows.join(", ")})` : ""}
                </span>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      {d.files_missing.length > 0 && (
        <p className="text-sm text-slate-500">
          {t("Not found in the data folder")}: {d.files_missing.join(", ")}
        </p>
      )}
    </Page>
  );
}
