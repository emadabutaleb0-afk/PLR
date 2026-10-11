"use client";
import "@xyflow/react/dist/style.css";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Background, Controls, Handle, MiniMap, Position, ReactFlow, ReactFlowProvider, useReactFlow, type Edge, type Node, type NodeProps } from "@xyflow/react";
import { Building2, Factory, MapPin, PackageSearch, Shirt, Target, Truck, X } from "lucide-react";
import { useApi } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n";
import { egp, num, pct } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Badge, Card } from "@/components/ui/primitives";
import { ErrorState, LoadingBlock } from "@/components/States";
import { ValueTag } from "@/components/ui/layout";

const KINDS: Record<string, { label: string; icon: any; color: string; col: number }> = {
  location: { label: "Locations", icon: MapPin, color: "var(--c-sky)", col: 0 }, decision: { label: "Open decisions", icon: Target, color: "var(--c-amber)", col: 1 },
  product: { label: "Products", icon: Shirt, color: "var(--series-gold)", col: 2 }, material: { label: "Materials", icon: PackageSearch, color: "var(--c-violet)", col: 3 },
  supplier: { label: "Suppliers", icon: Truck, color: "var(--c-green)", col: 4 }, unit: { label: "Business units", icon: Building2, color: "var(--c-muted)", col: 0 } };
const REL: Record<string, string> = { stocked_at: "stocked at", uses: "uses material", supplied_by: "supplied by", concerns: "concerns product", at_location: "at location" };
// metric label + formatter per data key: only keys that come from the API are shown
const FIELDS: Record<string, [string, (v: any) => string]> = {
  net_12m: ["Net sales, 12 months", (v) => egp(v, false)], units_12m: ["Units sold, 12 months", (v) => num(v)], stock: ["Stock on hand (units)", (v) => num(v)], stock_units: ["Stock on hand (units)", (v) => num(v)],
  days_of_cover: ["Days of cover", (v) => num(v, 1)], return_rate: ["Return rate", (v) => pct(v)], open_decisions: ["Open decisions", (v) => num(v)], open_decision_value_egp: ["Open decision value (estimate)", (v) => egp(v, false)],
  value_egp: ["Expected impact (estimate)", (v) => egp(v, false)], confidence: ["Confidence", (v) => pct(v, 0)], urgency: ["Urgency", (v) => String(v)], department: ["Department", (v) => String(v)], category: ["Type", (v) => String(v)],
  channel: ["Channel", (v) => String(v)], governorate: ["Governorate", (v) => String(v)], type: ["Type", (v) => String(v)], family: ["Family", (v) => String(v)], sku: ["SKU", (v) => String(v)], unit: ["Unit", (v) => String(v)],
  function: ["Function", (v) => String(v)], capacity: ["Public capacity", (v) => String(v)], purchase_orders: ["Purchase orders", (v) => num(v)], materials_in_view: ["Materials in this view", (v) => num(v)] };

function Entity({ data, selected }: NodeProps) {
  const k = KINDS[(data as any).kind]; const I = k.icon; const dim = (data as any).dim;
  return <div className={cn("w-[190px] rounded-xl border bg-surface px-3 py-2 shadow-card transition", selected ? "border-accent ring-2 ring-accent/40" : "border-line", dim && "opacity-25")} style={{ borderInlineStartColor: k.color, borderInlineStartWidth: 4 }}>
    <Handle type="target" position={Position.Left} className="!h-1.5 !w-1.5 !border-0 !bg-slate-400" /><div className="flex items-center gap-2"><I className="h-3.5 w-3.5 shrink-0" style={{ color: k.color }} />
      <span dir="auto" className="truncate text-xs font-semibold text-slate-900">{(data as any).label}</span></div><p dir="auto" className="mt-0.5 truncate text-[11px] text-slate-500">{(data as any).sub}</p>
    <Handle type="source" position={Position.Right} className="!h-1.5 !w-1.5 !border-0 !bg-slate-400" /></div>;
}
const nodeTypes = { entity: Entity };

function Inner() {
  const { t } = useI18n(); const sp = useSearchParams(); const router = useRouter(); const focus = sp.get("focus");
  const [limit, setLimit] = useState(10); const q = useApi<any>(`/workspace/network?limit=${limit}${focus ? `&focus=${encodeURIComponent(focus)}` : ""}`);
  const [sel, setSel] = useState<string | null>(null); const [hidden, setHidden] = useState<string[]>(["decision"]); const rf = useReactFlow();
  const d = q.data;
  const { nodes, edges } = useMemo(() => {
    if (!d) return { nodes: [] as Node[], edges: [] as Edge[] };
    // Open decisions are many (one per product x action): they are revealed per selected product, or all at once from the legend.
    const showDec = new Set<string>(); const selNode = d.nodes.find((n: any) => n.id === sel);
    if (selNode?.kind === "product") d.edges.forEach((e: any) => { if (e.rel === "concerns" && (e.target === sel || e.source === sel)) showDec.add(e.source === sel ? e.target : e.source); });
    if (selNode?.kind === "decision") showDec.add(sel!);
    const visible = d.nodes.filter((n: any) => n.kind === "decision" ? (!hidden.includes("decision") || showDec.has(n.id)) : !hidden.includes(n.kind)); const ids = new Set(visible.map((n: any) => n.id));
    const nb = new Set<string>(sel ? [sel] : []); if (sel) d.edges.forEach((e: any) => { if (e.source === sel) nb.add(e.target); if (e.target === sel) nb.add(e.source); });
    const H = 72; const per: Record<string, number> = {}; visible.forEach((n: any) => { if (n.kind !== "unit") per[n.kind] = (per[n.kind] ?? 0) + 1; });
    const tall = Math.max(1, ...Object.values(per)); const rows: Record<string, number> = {};
    const subOf = (n: any) => n.kind === "product" ? `${n.data.sku ?? ""} · ${num(n.data.stock)} ${t("units")}` : n.kind === "decision" ? `${egp(n.data.value_egp)} · ${t("estimate")}` : n.kind === "location" ? `${n.data.channel ?? n.data.type ?? ""}` : n.kind === "unit" ? `${n.data.function ?? ""}` : n.kind === "supplier" ? `${num(n.data.purchase_orders)} ${t("purchase orders")}` : n.data.unit ?? "";
    // one column per kind, each centred on the tallest column; business units sit in a row above because the data links them to nothing
    const ns: Node[] = visible.map((n: any) => { const k = KINDS[n.kind]; const r = (rows[n.kind] = (rows[n.kind] ?? -1) + 1);
      return { id: n.id, type: "entity", position: n.kind === "unit" ? { x: r * 210, y: -130 } : { x: k.col * 270, y: r * H + ((tall - (per[n.kind] ?? 1)) * H) / 2 }, data: { kind: n.kind, label: n.label, sub: subOf(n), dim: !!sel && !nb.has(n.id) }, selected: sel === n.id }; });
    const es: Edge[] = d.edges.filter((e: any) => ids.has(e.source) && ids.has(e.target)).map((e: any) => ({ id: e.id, source: e.source, target: e.target, animated: false,
      style: { stroke: sel && (e.source === sel || e.target === sel) ? "var(--series-gold)" : "var(--chart-axis)", strokeWidth: sel && (e.source === sel || e.target === sel) ? 2 : 1, opacity: sel && !(e.source === sel || e.target === sel) ? 0.12 : 0.55 } }));
    return { nodes: ns, edges: es };
  }, [d, hidden, sel, t]);
  useEffect(() => { if (d && focus) setSel(`product:${focus}`); }, [d, focus]);
  const sig = nodes.map((n) => n.id).join("|"); // re-fit the view whenever the set of visible cards changes, so nothing is left off-screen or microscopic
  useEffect(() => { if (!nodes.length) return; const id = setTimeout(() => rf.fitView({ padding: 0.15, maxZoom: 1, duration: 0 }), 60); return () => clearTimeout(id); }, [sig]); // eslint-disable-line react-hooks/exhaustive-deps
  if (q.error) return <ErrorState error={q.error} retry={q.refetch} />;
  if (q.isLoading || !d) return <LoadingBlock h="h-[32rem]" />;
  const node = d.nodes.find((n: any) => n.id === sel); const rels = node ? d.edges.filter((e: any) => e.source === sel || e.target === sel) : [];
  const nameOf = (id: string) => d.nodes.find((n: any) => n.id === id)?.label ?? id;
  const links = (n: any) => n.kind === "product" ? [[`/products/${n.ref}`, "Product 360"], [`/investigate?product=${n.ref}`, "Investigate"], [`/time-machine?product=${n.ref}`, "Time Machine"]] : n.kind === "decision" ? [[`/war-room?open=${encodeURIComponent(n.ref)}`, "Open in War Room"]] : n.kind === "supplier" ? [["/suppliers", "Supplier Control"]] : n.kind === "location" ? [[`/investigate?location=${n.ref}`, "Investigate"], ["/inventory", "Inventory Control"]] : [];
  const counts: Record<string, number> = {}; d.nodes.forEach((n: any) => { counts[n.kind] = (counts[n.kind] || 0) + 1; });
  return <div className="space-y-3">
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label={t("Show or hide groups")}>{Object.entries(KINDS).filter(([k]) => counts[k]).map(([k, v]) => { const off = hidden.includes(k); const I = v.icon;
      return <button key={k} aria-pressed={!off} onClick={() => setHidden((h) => off ? h.filter((x) => x !== k) : [...h, k])} className={cn("inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium", off ? "border-line text-slate-400 line-through" : "border-line-strong bg-surface text-slate-800")}><I className="h-3.5 w-3.5" style={{ color: v.color }} />{t(v.label)} <span className="tabular text-slate-500">{counts[k]}</span></button>; })}
      <label className="ms-auto flex items-center gap-2 text-xs text-slate-600">{t("Products shown")}<select value={limit} onChange={(e) => setLimit(Number(e.target.value))} className="h-8 rounded-lg border border-line bg-surface px-2 text-xs">{[8, 10, 20, 30, 50].map((x) => <option key={x}>{x}</option>)}</select></label>
      <span className="text-xs text-slate-500">{t("Showing {n} of {total} products (most open decision value first).", { n: d.shown_products, total: d.total_products })}</span></div>
    <div className="grid gap-3 xl:grid-cols-[1fr_340px]">
      <div dir="ltr" className="h-[min(38rem,72vh)] overflow-hidden rounded-2xl border border-line bg-surface" role="application" aria-label={t("Command map. Select a node to inspect it.")}>
        <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.15, maxZoom: 1 }} minZoom={0.15} maxZoom={1.8} nodesConnectable={false} nodesDraggable edgesFocusable={false}
          onNodeClick={(_, n) => setSel(n.id)} onPaneClick={() => setSel(null)} proOptions={{ hideAttribution: true }}>
          <Background gap={24} color="var(--chart-grid)" /><Controls showInteractive={false} /><MiniMap pannable zoomable nodeColor={(n: any) => KINDS[n.data.kind]?.color || "#999"} maskColor="rgb(var(--canvas) / 0.7)" /></ReactFlow></div>
      <Card className="max-h-[min(38rem,72vh)] space-y-3 overflow-y-auto p-4" aria-live="polite">{!node ? <div className="space-y-2 text-sm text-slate-600"><p className="font-semibold text-slate-900">{t("Select a node")}</p><p>{t("Click any card to see its real figures and what it is connected to. Lines are only drawn where the data really links two things.")}</p>
        <ul className="list-disc space-y-1 ps-5 text-xs text-slate-500">{d.notes.map((n: string, i: number) => <li key={i}>{t(n)}</li>)}</ul></div>
        : <><div className="flex items-start justify-between gap-2"><div><Badge kind="INFO">{t(KINDS[node.kind].label)}</Badge><h2 dir="auto" className="mt-1.5 text-base font-semibold">{node.label}</h2><p className="text-xs text-slate-500">{node.ref}</p></div><button onClick={() => setSel(null)} aria-label={t("Close")} className="rounded p-1 hover:bg-sunken"><X className="h-4 w-4" /></button></div>
          <dl className="space-y-1.5 text-sm">{Object.entries(node.data).filter(([k, v]) => FIELDS[k] && v != null && typeof v !== "object").map(([k, v]) => <div key={k} className="flex justify-between gap-3"><dt className="text-slate-500">{t(FIELDS[k][0])}</dt><dd className="tabular font-medium">{FIELDS[k][1](v)}</dd></div>)}
            {node.kind === "unit" && node.data.latest && <div className="rounded-lg bg-sunken p-2 text-xs"><p className="font-medium">{t("Latest group report")} ({node.data.latest.month})</p><p>{node.data.latest.kpi}: {num(node.data.latest.volume)} · {t("efficiency")} {num(node.data.latest.efficiency_pct, 1)}% · {t("open issues")} {num(node.data.latest.open_issues)}</p></div>}</dl>
          {node.kind === "decision" && <ValueTag kind="estimate" />}{node.kind === "unit" && <p className="text-xs text-slate-500">{t("Business units are not linked to products, locations or suppliers in the data, so no connections are drawn.")}</p>}
          {!!rels.length && <div><h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{t("Connected to")}</h3><ul className="space-y-1 text-sm">{rels.slice(0, 14).map((e: any) => { const other = e.source === sel ? e.target : e.source; return <li key={e.id}><button onClick={() => setSel(other)} className="flex w-full items-center justify-between gap-2 rounded-lg px-2 py-1 text-start hover:bg-sunken"><span dir="auto" className="truncate">{nameOf(other)}</span><span className="shrink-0 text-[11px] text-slate-500">{t(REL[e.rel])}</span></button></li>; })}</ul></div>}
          <div className="flex flex-wrap gap-2 pt-1">{links(node).map(([h, l]) => <Link key={h} href={h} className="rounded-lg border border-line px-2.5 py-1 text-xs font-medium hover:bg-sunken">{t(l)}</Link>)}
            {node.kind === "product" && focus !== node.ref && <button onClick={() => router.replace(`/map?focus=${node.ref}`)} className="rounded-lg border border-accent/50 px-2.5 py-1 text-xs font-medium hover:bg-accent/10">{t("Centre the map on this product")}</button>}</div></>}</Card></div>
    <p className="text-xs text-slate-500">{t("Keyboard: Tab to the map, then use the buttons in the legend to filter; the connected list on the right is the keyboard path to related items.")}</p>
  </div>;
}
export default function MapCanvas() { return <ReactFlowProvider><Inner /></ReactFlowProvider>; }
