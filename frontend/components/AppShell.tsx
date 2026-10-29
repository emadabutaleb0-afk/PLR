"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ChevronRight, Menu, PanelLeftClose, PanelLeftOpen, Search, X } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n";
import { useWorkspace } from "@/lib/workspace";
import { useTheme } from "@/lib/theme";
import { GROUPS, allowed, contextActions, crumbs } from "@/lib/nav";
import { cn } from "@/lib/utils";
import { BrandLockup, LogoBadge } from "./Brand";
import { ErrorBoundary } from "./ErrorBoundary";
import { CommandPalette } from "./shell/CommandPalette";
import { NotificationBell } from "./shell/NotificationBell";
import { UserMenu } from "./shell/UserMenu";
import { LangSwitch } from "./LangSwitch";
import { ThemeSwitch } from "./ThemeSwitch";

const isMac = () => typeof navigator !== "undefined" && /mac|iphone|ipad/i.test(navigator.platform || navigator.userAgent);

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { t, dir } = useI18n(); const { user, loading, can } = useAuth(); const path = usePathname(); const router = useRouter();
  const [open, setOpen] = useState(false); const { collapsed, toggleCollapsed, setPalette, hydrate } = useWorkspace(); const hydrateTheme = useTheme((s) => s.hydrate);
  const main = useRef<HTMLElement>(null); const first = useRef(true); const [mac, setMac] = useState(false);
  const notes = useApi(user ? "/workspace/notifications" : null, { refetchInterval: 120_000 });

  useEffect(() => { hydrate(); hydrateTheme(); setMac(isMac()); }, [hydrate, hydrateTheme]);
  useEffect(() => { if (!loading && !user) router.replace("/login"); }, [loading, user, router]);
  useEffect(() => { setOpen(false); if (first.current) { first.current = false; return; } main.current?.focus({ preventScroll: true }); }, [path]);

  // Accessibility: close mobile drawer on Escape key
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  if (loading || !user) return <div className="grid min-h-screen place-items-center"><LogoBadge size={64} className="animate-pulse" /></div>;
  const badge = (href: string) => href === "/war-room" ? notes.data?.totals?.approval : href === "/alerts" ? notes.data?.totals?.alert : href === "/notifications" ? notes.data?.total : undefined;
  const trail = crumbs(path); const actions = contextActions(path).filter((a) => allowed(a.scope, can));
  const rail = collapsed; // icon-only on desktop

  return <div className="min-h-screen">
    {open && <div className="fixed inset-0 z-30 bg-black/55 lg:hidden" onClick={() => setOpen(false)} aria-hidden />}
    <aside aria-label={t("Primary")} className={cn("fixed inset-y-0 start-0 z-40 flex w-72 flex-col overflow-y-auto overflow-x-hidden bg-ink-900 text-slate-300 transition-[transform,width] duration-200 lg:translate-x-0 lg:rtl:translate-x-0", open ? "translate-x-0 rtl:translate-x-0" : "-translate-x-full rtl:translate-x-full", rail ? "lg:w-[76px]" : "lg:w-[264px]")}>
      <div className={cn("flex items-center gap-2 px-4 pb-3 pt-4", rail && "lg:justify-center lg:px-2")}>
        {rail ? <LogoBadge size={36} className="hidden lg:inline-grid" /> : null}<div className={cn("min-w-0 flex-1", rail && "lg:hidden")}><BrandLockup dark showTagline={false} /></div>
        <button className="lg:hidden" onClick={() => setOpen(false)} aria-label={t("Close")}><X className="h-5 w-5 text-slate-400" /></button></div>
      <div className="hairline-gold mx-4 mb-3" />
      <nav className="flex-1 space-y-4 px-3 pb-3" aria-label={t("Main")}>{GROUPS.map((g) => { const items = g.items.filter((n) => allowed(n.scope, can)); if (!items.length) return null;
        return <div key={g.title}><p className={cn("mb-1 px-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500", rail && "lg:sr-only")}>{t(g.title)}</p>
          {rail && <div className="mx-3 mb-1 hidden h-px bg-white/10 lg:block" />}
          <ul className="space-y-0.5">{items.map((n) => { const a = n.href === "/" ? path === "/" : path === n.href || path.startsWith(n.href + "/"); const b = badge(n.href);
            return <li key={n.href}><Link href={n.href} aria-current={a ? "page" : undefined} title={rail ? t(n.label) : undefined} aria-label={rail ? t(n.label) : undefined}
              className={cn("group relative flex items-center gap-3 rounded-xl px-3 py-2 text-[13px] font-medium text-slate-400 transition-colors hover:bg-white/5 hover:text-white", a && "bg-white/10 text-white", rail && "lg:justify-center lg:px-0")}>
              {a && <span className="absolute inset-y-1.5 start-0 w-0.5 rounded-full bg-brand-500" />}<n.icon className={cn("h-4 w-4 shrink-0", a ? "text-brand-500" : "text-slate-500 group-hover:text-slate-300")} />
              <span className={cn("truncate", rail && "lg:sr-only")}>{t(n.label)}</span>
              {!!b && <span className={cn("ms-auto rounded-full bg-rose-500 px-1.5 text-[11px] font-semibold leading-5 text-white tabular", rail && "lg:absolute lg:end-1 lg:top-0.5 lg:ms-0 lg:px-1 lg:text-[9px] lg:leading-4")} aria-label={`${b}`}>{b}</span>}</Link></li>; })}</ul></div>; })}</nav>
      <div className="hidden border-t border-white/10 p-3 lg:block"><button onClick={toggleCollapsed} aria-label={rail ? t("Expand sidebar") : t("Collapse sidebar")} aria-pressed={rail} className={cn("flex w-full items-center gap-3 rounded-xl px-3 py-2 text-[13px] font-medium text-slate-400 hover:bg-white/5 hover:text-white", rail && "justify-center px-0")}>
        {rail ? <PanelLeftOpen className="h-4 w-4 rtl:rotate-180" /> : <PanelLeftClose className="h-4 w-4 rtl:rotate-180" />}<span className={cn(rail && "sr-only")}>{t("Collapse sidebar")}</span></button></div>
    </aside>
    <div className={cn("min-w-0 transition-[padding] duration-200", rail ? "lg:ps-[76px]" : "lg:ps-[264px]")}>
      <header className="sticky top-0 z-30 border-b border-line bg-canvas/85 backdrop-blur">
        <div className="flex h-14 items-center gap-2 px-3 sm:px-4 lg:px-8">
          <button className="grid h-9 w-9 place-items-center rounded-xl hover:bg-sunken lg:hidden" onClick={() => setOpen(true)} aria-label={t("Menu")} aria-expanded={open}><Menu className="h-5 w-5" /></button>
          <nav aria-label={t("Breadcrumb")} className="hidden min-w-0 items-center gap-1 text-sm md:flex"><ol className="flex min-w-0 items-center gap-1">{trail.map((c, i) => <li key={i} className="flex min-w-0 items-center gap-1">
            {i > 0 && <ChevronRight className="h-3.5 w-3.5 shrink-0 text-slate-400 rtl:rotate-180" />}
            {c.href ? <Link href={c.href} className="truncate text-slate-500 hover:text-slate-900">{t(c.label)}</Link> : <span className={cn("truncate", i === trail.length - 1 ? "font-semibold text-slate-900" : "text-slate-500")} aria-current={i === trail.length - 1 ? "page" : undefined}>{t(c.label)}</span>}</li>)}</ol></nav>
          <button onClick={() => setPalette(true)} aria-haspopup="dialog" aria-keyshortcuts="Control+K Meta+K" className="mx-auto flex h-9 w-full max-w-md items-center gap-2 rounded-xl border border-line bg-surface px-3 text-sm text-slate-500 hover:border-line-strong md:mx-0 md:ms-auto">
            <Search className="h-4 w-4" /><span className="flex-1 truncate text-start">{t("Search or jump to…")}</span><kbd className="hidden rounded border border-line px-1.5 py-0.5 text-[11px] sm:block">{mac ? "⌘" : "Ctrl"} K</kbd></button>
          <div className="ms-auto flex items-center gap-1.5 md:ms-0"><LangSwitch className="h-8 px-2.5 text-xs shadow-none border-line bg-surface" /><ThemeSwitch className="h-8 w-8 text-xs shadow-none border-line bg-surface" /><NotificationBell /><UserMenu /></div>
        </div>
        {!!actions.length && <div className="hidden items-center gap-2 border-t border-line px-4 py-1.5 text-xs md:flex lg:px-8"><span className="text-slate-500">{t("Related")}:</span>{actions.map((a) => <Link key={a.href} href={a.href} className="rounded-lg border border-line px-2.5 py-1 font-medium text-slate-700 hover:bg-sunken">{t(a.label)}</Link>)}</div>}
      </header>
      <main id="main" ref={main} tabIndex={-1} dir={dir} className="mx-auto max-w-[1560px] p-4 outline-none lg:p-8"><ErrorBoundary resetKey={path}>{children}</ErrorBoundary></main>
    </div>
    <CommandPalette />
  </div>;
}
