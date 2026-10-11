"use client";
import Link from "next/link";
import { Check, LogOut, Monitor, Moon, Sun, UserCog } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { useTheme, ThemeMode } from "@/lib/theme";
import { useWorkspace } from "@/lib/workspace";
import { Popover } from "../ui/popover";
import { cn } from "@/lib/utils";

const initials = (s: string) => s.split(/[\s@.]+/).filter(Boolean).slice(0, 2).map((x) => x[0]?.toUpperCase()).join("");
/** Workspace settings: appearance, language, sidebar default, account, sign out. Stored on this device only. */
export function UserMenu() {
  const { t, lang, setLang } = useI18n(); const { user, logout } = useAuth(); const { mode, setMode } = useTheme(); const { collapsed, toggleCollapsed } = useWorkspace();
  if (!user) return null;
  const MODES: { k: ThemeMode; label: string; icon: any }[] = [{ k: "light", label: "Light", icon: Sun }, { k: "dark", label: "Dark", icon: Moon }, { k: "system", label: "System", icon: Monitor }];
  const Opt = ({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) => <button onClick={onClick} aria-pressed={on} className={cn("flex flex-1 items-center justify-center gap-1.5 rounded-lg border px-2 py-1.5 text-xs font-medium", on ? "border-accent bg-accent/10 text-slate-900" : "border-line text-slate-600 hover:bg-sunken")}>{children}</button>;
  return <Popover label={t("Workspace settings")} trigger={({ open, toggle, ref, id }) =>
    <button ref={ref} onClick={toggle} aria-haspopup="true" aria-expanded={open} aria-controls={id} aria-label={t("Workspace settings")} className="grid h-9 w-9 place-items-center rounded-full bg-ink-800 text-xs font-semibold text-brand-300 ring-1 ring-brand-500/40 hover:ring-brand-400">{initials(user.full_name || user.email)}</button>}>
    {(close) => <div className="space-y-3 p-2">
      <div><p className="truncate text-sm font-semibold">{user.full_name || user.email}</p><p className="truncate text-xs text-slate-500">{user.email} · {t(user.role)}</p>{user.allowed_locations && <p className="text-xs text-slate-500">{t("Locations")}: {user.allowed_locations.join(", ")}</p>}</div>
      <div><p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500">{t("Appearance")}</p><div className="flex gap-1.5">{MODES.map((m) => <Opt key={m.k} on={mode === m.k} onClick={() => setMode(m.k)}><m.icon className="h-3.5 w-3.5" />{t(m.label)}</Opt>)}</div></div>
      <div><p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500">{t("Language")}</p><div className="flex gap-1.5"><Opt on={lang === "en"} onClick={() => setLang("en")}>English</Opt><Opt on={lang === "ar"} onClick={() => setLang("ar")}>العربية</Opt></div></div>
      <button onClick={toggleCollapsed} className="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-sm hover:bg-sunken" role="switch" aria-checked={collapsed}>{t("Compact sidebar")}<span className={cn("grid h-5 w-5 place-items-center rounded border", collapsed ? "border-accent bg-accent text-accent-fg" : "border-line-strong")}>{collapsed && <Check className="h-3.5 w-3.5" />}</span></button>
      <p className="px-2 text-[11px] text-slate-500">{t("These settings are saved on this device only.")}</p>
      <div className="border-t border-line pt-1.5"><Link href="/account" onClick={close} className="flex items-center gap-2 rounded-lg px-2 py-2 text-sm hover:bg-sunken"><UserCog className="h-4 w-4 text-slate-500" />{t("My account")}</Link>
        <button onClick={logout} className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm hover:bg-sunken"><LogOut className="h-4 w-4 text-slate-500 rtl:rotate-180" />{t("Sign out")}</button></div>
    </div>}</Popover>;
}
