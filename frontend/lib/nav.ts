import { Bell, Boxes, ClipboardList, Database, Factory, FlaskConical, Flame, HelpCircle, Home, Presentation, UserSearch, LayoutDashboard, Megaphone, PackageSearch, Percent, ShieldCheck, Shirt, Split, Target, TrendingUp, Truck, Users, Workflow, Network, History, Columns2, SquareKanban, BellRing, FileBarChart } from "lucide-react";

/** One navigation model for the sidebar, breadcrumbs and the command palette. `scope` "" = any signed-in user; otherwise the backend scope that gates the API behind the page. */
export type NavItem = { href: string; label: string; icon: any; scope: string; keywords?: string };
export type NavGroup = { title: string; items: NavItem[] };
export const GROUPS: NavGroup[] = [
  { title: "Command", items: [
    { href: "/", label: "Command Center", icon: Home, scope: "alerts", keywords: "home today" },
    { href: "/dashboard", label: "Executive Dashboard", icon: LayoutDashboard, scope: "executive", keywords: "kpi revenue profit" },
    { href: "/demo", label: "Demo Story", icon: Presentation, scope: "executive", keywords: "presentation" }] },
  { title: "Workspaces", items: [
    { href: "/war-room", label: "Decision War Room", icon: SquareKanban, scope: "recovery", keywords: "board approve decisions kanban" },
    { href: "/map", label: "Command Map", icon: Network, scope: "products", keywords: "network graph relationships supplier location" },
    { href: "/time-machine", label: "Time Machine", icon: History, scope: "products", keywords: "history timeline before after" },
    { href: "/investigate", label: "Investigation", icon: Columns2, scope: "products", keywords: "split compare product" },
    { href: "/notifications", label: "Notification Center", icon: BellRing, scope: "", keywords: "approvals tasks inbox" },
    { href: "/analytics", label: "Advanced Analytics", icon: FileBarChart, scope: "export", keywords: "power bi reports export" }] },
  { title: "Decide", items: [
    { href: "/recovery", label: "Recovery Priorities", icon: Target, scope: "recovery" },
    { href: "/decisions", label: "Decision Plans", icon: Workflow, scope: "recovery", keywords: "portfolio optimizer tracking outcomes" },
    { href: "/actions", label: "Action Center", icon: ClipboardList, scope: "actions" },
    { href: "/alerts", label: "Alert Center", icon: Bell, scope: "alerts" }] },
  { title: "Intelligence", items: [
    { href: "/leakage", label: "Profit Leakage", icon: Flame, scope: "executive" },
    { href: "/autopsy", label: "Business Autopsy", icon: FlaskConical, scope: "executive", keywords: "why profit changed" },
    { href: "/allocation", label: "Channel Allocation", icon: Split, scope: "inventory" },
    { href: "/discounts", label: "Discount Intelligence", icon: Percent, scope: "costs" },
    { href: "/scenarios", label: "What-if Scenarios", icon: FlaskConical, scope: "costs" },
    { href: "/supply", label: "Supply Readiness", icon: Workflow, scope: "suppliers" },
    { href: "/customers", label: "Customer Intelligence", icon: UserSearch, scope: "executive" }] },
  { title: "Control", items: [
    { href: "/products", label: "Products", icon: Shirt, scope: "products" },
    { href: "/merchandising", label: "Merchandising", icon: Boxes, scope: "products" },
    { href: "/inventory", label: "Inventory Control", icon: PackageSearch, scope: "inventory" },
    { href: "/marketing", label: "Marketing Control", icon: Megaphone, scope: "marketing" },
    { href: "/suppliers", label: "Supplier Control", icon: Truck, scope: "suppliers" },
    { href: "/quality", label: "Quality Control", icon: ShieldCheck, scope: "quality" },
    { href: "/operations", label: "Operations Control", icon: Factory, scope: "operations" }] },
  { title: "Governance", items: [
    { href: "/value", label: "Value Realization", icon: TrendingUp, scope: "value" },
    { href: "/data", label: "Data Health", icon: Database, scope: "data_health" },
    { href: "/users", label: "Users & Access", icon: Users, scope: "users_admin" },
    { href: "/method", label: "How numbers are calculated", icon: HelpCircle, scope: "alerts" }] },
];
export const ALL_ITEMS = GROUPS.flatMap((g) => g.items.map((i) => ({ ...i, group: g.title })));
export const allowed = (scope: string, can: (s: string) => boolean) => !scope || can(scope);

/** Breadcrumb trail for a path: group > page > (record). */
export function crumbs(path: string): { label: string; href?: string }[] {
  if (path === "/" ) return [{ label: "Command Center" }];
  const hit = [...ALL_ITEMS].filter((i) => i.href !== "/" && (path === i.href || path.startsWith(i.href + "/"))).sort((a, b) => b.href.length - a.href.length)[0];
  if (path.startsWith("/account")) return [{ label: "Account" }, { label: "My account" }];
  if (!hit) return [{ label: path.split("/").filter(Boolean)[0] || "" }];
  const out: { label: string; href?: string }[] = [{ label: hit.group }, { label: hit.label, href: path === hit.href ? undefined : hit.href }];
  if (path !== hit.href) out.push({ label: decodeURIComponent(path.slice(hit.href.length + 1).split("/")[0]) });
  return out;
}

/** Contextual quick actions shown in the header for the current area. Links only: nothing here changes business data. */
export function contextActions(path: string): { label: string; href: string; scope: string }[] {
  const m = path.match(/^\/products\/([^/]+)/);
  if (m) return [{ label: "Investigate", href: `/investigate?product=${m[1]}`, scope: "products" }, { label: "Time Machine", href: `/time-machine?product=${m[1]}`, scope: "products" }, { label: "Show on map", href: `/map?focus=${m[1]}`, scope: "products" }];
  if (path.startsWith("/war-room")) return [{ label: "Decision plans", href: "/decisions", scope: "recovery" }, { label: "Outcomes", href: "/decisions?tab=tracking", scope: "value" }];
  if (path.startsWith("/map")) return [{ label: "Investigation", href: "/investigate", scope: "products" }];
  if (path.startsWith("/dashboard")) return [{ label: "War Room", href: "/war-room", scope: "recovery" }];
  return [];
}
