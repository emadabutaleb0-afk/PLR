"use client";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { Page } from "@/components/Page";
import { Button, Card, Input, Label } from "@/components/ui/primitives";
import { LangSwitch } from "@/components/LangSwitch";
export default function Account() {
  const { t } = useI18n(); const { user } = useAuth(); const [cur, setCur] = useState(""); const [n1, setN1] = useState(""); const [n2, setN2] = useState(""); const [err, setErr] = useState(""); const [ok, setOk] = useState(false);
  const m = useMutation({ mutationFn: () => api("/auth/change-password", { method: "POST", body: JSON.stringify({ current_password: cur, new_password: n1 }) }), onSuccess: () => { setOk(true); setCur(""); setN1(""); setN2(""); setErr(""); }, onError: (e: any) => { setOk(false); setErr(e.message); } });
  const go = () => { setOk(false); if (n1.length < 10) return setErr(t("The new password must be at least 10 characters.")); if (n1 !== n2) return setErr(t("The two new passwords do not match.")); setErr(""); m.mutate(); };
  return <Page title="My account" sub="Your profile, language and password.">
    <Card className="space-y-2 p-5 text-sm"><p className="font-semibold">{user?.full_name || user?.email}</p><p dir="ltr" className="text-slate-500">{user?.email}</p><p className="text-slate-500">{t(user?.role || "")}</p><div className="pt-2"><LangSwitch /></div></Card>
    <Card className="max-w-md space-y-4 p-5"><h3 className="font-semibold">{t("Change password")}</h3>
      <div><Label>{t("Current password")}</Label><Input dir="ltr" type="password" autoComplete="current-password" value={cur} onChange={(e) => setCur(e.target.value)} /></div>
      <div><Label>{t("New password")}</Label><Input dir="ltr" type="password" autoComplete="new-password" value={n1} onChange={(e) => setN1(e.target.value)} /></div>
      <div><Label>{t("Repeat new password")}</Label><Input dir="ltr" type="password" autoComplete="new-password" value={n2} onChange={(e) => setN2(e.target.value)} /></div>
      {err && <p className="rounded-lg bg-rose-50 p-2.5 text-sm text-rose-700" role="alert">{err}</p>}{ok && <p className="rounded-lg bg-emerald-50 p-2.5 text-sm text-emerald-700">{t("Password changed.")}</p>}
      <Button disabled={m.isPending || !cur || !n1} onClick={go}>{t("Save")}</Button></Card></Page>;
}
