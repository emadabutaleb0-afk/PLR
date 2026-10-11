"use client";
import { useState } from "react";
import { Download, ShieldCheck } from "lucide-react";
import { useApi } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n";
import { download } from "@/lib/api";
import { Page, Panel } from "@/components/Page";
import { Badge, Button, Card } from "@/components/ui/primitives";
import { ErrorState, LoadingBlock } from "@/components/States";

export default function Analytics() {
  const { t } = useI18n(); const q = useApi<any>("/workspace/reports"); const [busy, setBusy] = useState<string | null>(null); const [err, setErr] = useState<string | null>(null);
  const get = async (r: any, fmt: "csv" | "xlsx") => { setBusy(r.id + fmt); setErr(null); try { await download(`/export/${r.dataset}?format=${fmt}`, `${r.dataset}.${fmt}`); } catch (e: any) { setErr(e.message); } finally { setBusy(null); } };
  if (q.error) return <Page title="Advanced Analytics"><ErrorState error={q.error} retry={q.refetch} /></Page>;
  return <Page title="Advanced Analytics" sub="Approved reporting views for Power BI or Excel. Everything stays on the company network." fresh={q.data?.freshness}>
    {q.isLoading || !q.data ? <LoadingBlock /> : <>
      <Panel title="Approved reporting views" hint="Each view is the same data the application shows, filtered by your role: cost columns and other locations' rows are removed if you are not allowed to see them.">
        <ul className="divide-y divide-line">{q.data.reports.map((r: any) => <li key={r.id} className="flex flex-wrap items-center gap-3 py-3"><div className="min-w-0 flex-1"><p className="font-medium">{t(r.title)}</p><p className="text-xs text-slate-500">{t("Grain")}: {t(r.grain)} · {t("Refreshed")}: {t(r.refresh)}</p><code className="mt-1 inline-block rounded bg-sunken px-1.5 py-0.5 text-[11px]">{r.endpoint}</code></div>
          {r.available ? <div className="flex gap-2">{r.formats.map((f: string) => <Button key={f} size="sm" variant="outline" disabled={busy === r.id + f} onClick={() => get(r, f as any)}><Download className="h-3.5 w-3.5" />{f.toUpperCase()}</Button>)}</div> : <Badge kind="STALE">{t("Export not enabled for your role")}</Badge>}</li>)}
          {!q.data.reports.length && <li className="py-6 text-sm text-slate-500">{t("No reporting views are available for your role.")}</li>}</ul>{err && <p role="alert" className="mt-2 text-sm text-rose-600">{err}</p>}</Panel>
      <Card className="p-5"><h2 className="flex items-center gap-2 font-semibold"><ShieldCheck className="h-4 w-4 text-emerald-600" />{t("Power BI readiness: what is and is not in place")}</h2>
        <ul className="mt-3 list-disc space-y-2 ps-5 text-sm text-slate-700">{q.data.requirements.map((x: string, i: number) => <li key={i}>{t(x)}</li>)}</ul>
        <div className="mt-4 grid gap-3 text-sm md:grid-cols-3">{[["Ready now", "Export files with role-based filtering, an audit trail of every export, and a read-only reporting catalogue."], ["Needs IT decision", "Power BI Report Server or licensed capacity, a service account, and how users sign in to reports."], ["Not built", "Embedding Power BI reports in this application, scheduled refresh, row-level security inside Power BI."]].map(([h, b]) => <div key={h} className="rounded-xl bg-sunken p-3"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t(h)}</p><p className="mt-1">{t(b)}</p></div>)}</div></Card></>}
  </Page>;
}
