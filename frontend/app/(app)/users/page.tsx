"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, KeyRound, Wand2 } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n";
import { Page } from "@/components/Page";
import { ErrorState, LoadingBlock } from "@/components/States";
import { Badge, Button, Card, Input, Label, Select } from "@/components/ui/primitives";
const ROLES = ["CEO", "EXECUTIVE", "OPERATIONS_MANAGER", "PRODUCTION_MANAGER", "MARKETING_MANAGER", "STORE_MANAGER", "ANALYST"];
const ROLE_HINT: Record<string, string> = { CEO: "Full access, including users and data import", EXECUTIVE: "Everything except user admin and data import", OPERATIONS_MANAGER: "Operations, inventory, suppliers, quality, costs",
  PRODUCTION_MANAGER: "Production, quality, suppliers (no costs)", MARKETING_MANAGER: "Marketing, products, inventory (no costs, no suppliers)", STORE_MANAGER: "Only the locations assigned to them", ANALYST: "Read-only analytics, models and data import" };
const genPw = () => { const c = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"; const a = new Uint32Array(14); crypto.getRandomValues(a); return Array.from(a, (x) => c[x % c.length]).join("") + "!7"; };
type Form = { id?: number; email: string; full_name: string; role: string; password: string; allowed_locations: string[]; is_active: boolean };
const blank: Form = { email: "", full_name: "", role: "ANALYST", password: "", allowed_locations: [], is_active: true };
export default function UsersPage() {
  const { t } = useI18n(); const { user } = useAuth(); const qc = useQueryClient();
  const users = useApi("/auth/users"); const locs = useApi("/auth/locations");
  const [f, setF] = useState<Form | null>(null); const [err, setErr] = useState(""); const [made, setMade] = useState<{ email: string; pw: string } | null>(null);
  const save = useMutation({
    mutationFn: async (v: Form) => v.id
      ? api(`/auth/users/${v.id}`, { method: "PATCH", body: JSON.stringify({ full_name: v.full_name, role: v.role, is_active: v.is_active, allowed_locations: v.role === "STORE_MANAGER" ? v.allowed_locations : [], ...(v.password ? { password: v.password } : {}) }) })
      : api("/auth/users", { method: "POST", body: JSON.stringify({ email: v.email, full_name: v.full_name, role: v.role, password: v.password, allowed_locations: v.role === "STORE_MANAGER" ? v.allowed_locations : null }) }),
    onSuccess: (_r, v) => { if (v.password) setMade({ email: v.email, pw: v.password }); setF(null); setErr(""); qc.invalidateQueries({ queryKey: ["/auth/users"] }); }, onError: (e: any) => setErr(e.message) });
  if (users.error) return <ErrorState error={users.error} retry={users.refetch} />; if (users.isLoading || !users.data) return <LoadingBlock />;
  const toggleLoc = (id: string) => setF((p) => p && ({ ...p, allowed_locations: p.allowed_locations.includes(id) ? p.allowed_locations.filter((x) => x !== id) : [...p.allowed_locations, id] }));
  return <Page title="Users & Access" sub="Create accounts for your team and choose what each person can see." right={<Button onClick={() => { setF({ ...blank, password: genPw() }); setErr(""); }}><Plus className="h-4 w-4" />{t("Add user")}</Button>}>
    {made && <Card className="space-y-1 border-emerald-200 bg-emerald-50 p-4 text-sm"><p className="font-semibold text-emerald-800">{t("Share these sign-in details with the user (the password is shown only now):")}</p><p dir="ltr" className="font-mono">{made.email} / {made.pw}</p><Button size="sm" variant="outline" onClick={() => setMade(null)}>{t("Done")}</Button></Card>}
    {f && <Card className="space-y-4 p-5"><h3 className="font-semibold">{f.id ? t("Edit user") : t("New user")}</h3>
      <div className="grid gap-4 md:grid-cols-2">
        <div><Label>{t("Full name")}</Label><Input value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} /></div>
        <div><Label>{t("Work email")}</Label><Input dir="ltr" type="email" disabled={!!f.id} value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></div>
        <div><Label>{t("Role")}</Label><Select className="h-10 w-full" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}>{ROLES.map((r) => <option key={r} value={r}>{t(r)}</option>)}</Select><p className="mt-1 text-xs text-slate-500">{t(ROLE_HINT[f.role])}</p></div>
        <div><Label>{f.id ? t("Reset password (leave empty to keep)") : t("Password (min 10 characters)")}</Label><div className="flex gap-2"><Input dir="ltr" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /><Button type="button" variant="outline" size="icon" onClick={() => setF({ ...f, password: genPw() })} aria-label={t("Generate")}><Wand2 className="h-4 w-4" /></Button></div></div></div>
      {f.role === "STORE_MANAGER" && <div><Label>{t("Allowed locations")}</Label><div className="flex flex-wrap gap-3">{(locs.data || []).map((l: any) => <label key={l.location_id} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.allowed_locations.includes(l.location_id)} onChange={() => toggleLoc(l.location_id)} />{l.location_name}</label>)}</div></div>}
      {f.id && <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.is_active} onChange={(e) => setF({ ...f, is_active: e.target.checked })} />{t("Account is active")}</label>}
      {err && <p className="rounded-lg bg-rose-50 p-2.5 text-sm text-rose-700" role="alert">{err}</p>}
      <div className="flex gap-2"><Button disabled={save.isPending} onClick={() => save.mutate(f)}>{t("Save")}</Button><Button variant="outline" onClick={() => { setF(null); setErr(""); }}>{t("Cancel")}</Button></div></Card>}
    <Card className="overflow-auto"><table className="w-full text-sm"><thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr>{["Name", "Email", "Role", "Status", ""].map((c, i) => <th key={i} className="px-3 py-2.5 text-start font-medium">{t(c)}</th>)}</tr></thead>
      <tbody className="divide-y">{users.data.map((u: any) => <tr key={u.id}><td className="px-3 py-2.5 font-medium">{u.full_name || "—"}{u.id === user?.id && <span className="ms-2 text-xs text-slate-400">({t("you")})</span>}</td><td className="px-3" dir="ltr">{u.email}</td>
        <td className="px-3">{t(u.role)}{u.allowed_locations && <span className="block text-xs text-slate-400">{u.allowed_locations.join(", ")}</span>}</td><td className="px-3"><Badge kind={u.is_active ? "OK" : "LOW"}>{u.is_active ? t("Active") : t("Disabled")}</Badge></td>
        <td className="px-3 text-end"><Button size="sm" variant="outline" onClick={() => { setF({ id: u.id, email: u.email, full_name: u.full_name, role: u.role, password: "", allowed_locations: u.allowed_locations || [], is_active: u.is_active }); setErr(""); }}><KeyRound className="h-3.5 w-3.5" />{t("Edit")}</Button></td></tr>)}</tbody></table></Card></Page>;
}
