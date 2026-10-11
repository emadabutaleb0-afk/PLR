"use client";
import { Bar, BarChart, CartesianGrid, Legend, Tooltip, XAxis, YAxis } from "recharts";
import { useApi } from "@/lib/hooks";
import { egp, pct, axisK } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { Page, Panel, Stat } from "@/components/Page";
import { ChartBox, axis } from "@/components/Chart";
import { ErrorState, LoadingBlock, Empty } from "@/components/States";
export default function Value() {
  const { t } = useI18n(); const { data: d, error, isLoading, refetch } = useApi("/value/summary");
  if (error) return <ErrorState error={error} retry={refetch} />; if (isLoading || !d) return <LoadingBlock />;
  return <Page title="Value Realization" sub={`${t("Proof that the platform creates money")} — ${d.month}`} fresh={d.freshness}>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><Stat label="Recommendations this month" value={d.recommendations_generated} /><Stat label="Accepted" value={`${d.accepted}`} /><Stat label="Estimated business value" value={egp(d.expected_value_egp)} /><Stat label="Realized business value" value={egp(d.realized_value_egp)} tone="text-emerald-600" /></div>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><Stat label="Recovered profit" value={egp(d.recovered_profit_egp)} /><Stat label="Loss avoided" value={egp(d.loss_avoided_egp)} /><Stat label="Revenue protected" value={egp(d.revenue_protected_egp)} /><Stat label="Acceptance rate" value={pct(d.acceptance_rate, 0)} /></div>
    <Panel title="Expected vs realized value by month" hint={d.note}>{d.monthly?.length ? <ChartBox h={280}><BarChart data={d.monthly}><CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" /><XAxis dataKey="month" tick={axis} /><YAxis tick={axis} tickFormatter={(v) => axisK(v)} /><Tooltip formatter={(v: any) => egp(v, false)} /><Legend /><Bar dataKey="expected" name={t("Expected")} fill="var(--c-soft2)" /><Bar dataKey="realized" name={t("Realized")} fill="var(--c-green)" /></BarChart></ChartBox> : <Empty title="No accepted recommendations yet" hint="Accept a recommendation, act on it, then record the real outcome to see realised value here." />}</Panel>
    <p className="text-sm text-slate-500">{t("Outcomes recorded")}: <b>{d.outcomes_recorded}</b> {t("of")} {d.accepted} {t("accepted")}{d.realization_rate !== null && <> · {t("realised vs expected")}: <b>{pct(d.realization_rate, 0)}</b></>}</p></Page>;
}
