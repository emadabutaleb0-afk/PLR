"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { Button, Card, Input, Label } from "@/components/ui/primitives";
import { LangSwitch } from "@/components/LangSwitch";
import { BRAND, LogoBadge } from "@/components/Brand";
export default function Login() {
  const { t } = useI18n(); const { login, user, loading } = useAuth(); const r = useRouter();
  const [email, setE] = useState(""); const [pw, setP] = useState(""); const [show, setShow] = useState(false); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  useEffect(() => { if (!loading && user) r.replace("/"); }, [loading, user, r]);
  const submit = async (e: React.FormEvent) => { e.preventDefault(); setBusy(true); setErr(""); try { await login(email.trim(), pw); r.replace("/"); } catch (x: any) { setErr(x.message); } finally { setBusy(false); } };
  return <div className="brand-grad relative grid min-h-screen place-items-center p-4">
    <div className="absolute end-4 top-4"><LangSwitch className="border-white/20 bg-white/10 text-white hover:bg-white/20" /></div>
    <Card className="w-full max-w-sm p-8 shadow-2xl">
      <div className="mb-7 flex flex-col items-center text-center"><LogoBadge size={96} /><h1 className="mt-4 text-xl font-bold tracking-[0.2em]">{BRAND.name}</h1><p className="mt-0.5 text-sm font-medium text-brand-700">{t(BRAND.company)}</p><div className="hairline-gold my-3 w-24" /><p className="text-xs uppercase tracking-wider text-slate-500">{t(BRAND.tagline)}</p></div>
      <form onSubmit={submit} className="space-y-4">
        <div><Label htmlFor="email">{t("Work email")}</Label><Input id="email" type="email" autoComplete="username" dir="ltr" value={email} onChange={(e) => setE(e.target.value)} required autoFocus /></div>
        <div><Label htmlFor="pw">{t("Password")}</Label><div className="relative"><Input id="pw" type={show ? "text" : "password"} autoComplete="current-password" dir="ltr" className="pe-10" value={pw} onChange={(e) => setP(e.target.value)} required />
          <button type="button" className="absolute end-3 top-3 text-slate-400 hover:text-slate-600" onClick={() => setShow(!show)} aria-label={show ? t("Hide password") : t("Show password")}>{show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button></div></div>
        {err && <p className="rounded-lg bg-rose-50 p-2.5 text-sm text-rose-700" role="alert">{err}</p>}
        <Button className="w-full" disabled={busy}>{busy ? t("Signing in…") : t("Sign in")}</Button></form>
      <p className="mt-4 text-center text-xs text-slate-400">{t("Runs entirely inside your company network. No data leaves your servers.")}</p></Card></div>;
}
