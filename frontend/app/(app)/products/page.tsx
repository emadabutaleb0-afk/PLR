"use client";
import { useState } from "react";
import Link from "next/link";
import { createColumnHelper } from "@tanstack/react-table";
import { useApi } from "@/lib/hooks";
import { ACTION_LABEL, egp, num, pct } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { Page } from "@/components/Page";
import { DataTable, defaultQuery, qs } from "@/components/DataTable";
import { ErrorState } from "@/components/States";
import { Badge, Select } from "@/components/ui/primitives";
const h = createColumnHelper<any>();
export default function Products() {
  const { t } = useI18n(); const [q, setQ] = useState(defaultQuery("net_12m")); const [action, setAction] = useState("");
  const { data, error, isLoading, refetch } = useApi(`/products?${qs(q, { action })}`);
  const cols = [h.accessor("product_name", { header: "Product", cell: (i) => <Link className="font-medium text-brand-700 hover:underline" href={`/products/${i.row.original.product_id}`}>{i.getValue()}<span className="block text-xs font-normal text-slate-400">{i.row.original.sku}</span></Link> }),
    h.accessor("product_family", { header: "Family" }), h.accessor("net_12m", { header: "Sales (12m)", cell: (i) => egp(i.getValue()) }),
    ...(data?.items?.[0] && "margin_12m" in data.items[0] ? [h.accessor("margin_12m", { header: "Margin", cell: (i) => pct(i.getValue()) })] : []),
    h.accessor("stock", { header: "Stock", cell: (i) => num(i.getValue()) }), h.accessor("days_of_cover", { header: "Days of cover", cell: (i) => num(i.getValue(), 0) }), h.accessor("return_rate", { header: "Return rate", cell: (i) => pct(i.getValue()) }),
    h.accessor("recommended_action", { header: "Action", cell: (i) => <Badge kind={i.row.original.action_urgency}>{t(ACTION_LABEL[i.getValue()] || i.getValue())}</Badge> }),
    h.accessor("action_value_egp", { header: "Impact", cell: (i) => i.getValue() ? <span className="text-emerald-600">{egp(i.getValue())}</span> : "—" })];
  if (error) return <ErrorState error={error} retry={refetch} />;
  return <Page title="Products" sub="Every product with its current recommended action." fresh={data?.freshness}>
    <DataTable columns={cols} data={data?.items || []} total={data?.total || 0} pages={data?.pages || 1} query={q} setQuery={setQ} loading={isLoading} exportPath="/export/products?format=csv" exportName="products.csv"
      filters={<Select value={action} onChange={(e) => { setAction(e.target.value); setQ({ ...q, page: 1 }); }} aria-label={t("Action")}><option value="">{t("All actions")}</option>{Object.entries(ACTION_LABEL).map(([k, v]) => <option key={k} value={k}>{t(v)}</option>)}</Select>} /></Page>;
}
