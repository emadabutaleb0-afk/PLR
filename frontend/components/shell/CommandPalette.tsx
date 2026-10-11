"use client";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import { CornerDownLeft, Download, Languages, LogOut, Moon, PanelLeft, Search, SquareKanban, Sun } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import { api, download } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { useTheme, resolveTheme } from "@/lib/theme";
import { useWorkspace } from "@/lib/workspace";
import { ALL_ITEMS, allowed } from "@/lib/nav";
import { egp } from "@/lib/format";

type Row = { id: string; label: string; sub?: string; icon?: any; run: () => void; tag?: string };

/** Ctrl/Cmd+K. Everything listed is filtered by the signed-in user's scopes; the server still enforces them on every call.
 *  Navigation, theme, language and read-only exports only: approving or changing a business record is never done from here. */
export function CommandPalette() {
  const { t, lang, setLang } = useI18n(); const { can, logout } = useAuth(); const r = useRouter();
  const { paletteOpen: open, setPalette, toggleCollapsed } = useWorkspace(); const { mode, setMode } = useTheme();
  const [q, setQ] = useState(""); const [remote, setRemote] = useState<any[]>([]); const [busy, setBusy] = useState(false);
  useEffect(() => { const f = (e: KeyboardEvent) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPalette(!useWorkspace.getState().paletteOpen); } }; window.addEventListener("keydown", f); return () => window.removeEventListener("keydown", f); }, [setPalette]);
  useEffect(() => { if (!open) { setQ(""); setRemote([]); } }, [open]);
  useEffect(() => { if (!open || q.trim().length < 2) { setRemote([]); return; } let live = true; setBusy(true);
    const id = setTimeout(() => api(`/search?q=${encodeURIComponent(q.trim())}`).then((x) => live && setRemote(x.results || [])).catch(() => live && setRemote([])).finally(() => live && setBusy(false)), 220);
    return () => { live = false; clearTimeout(id); }; }, [q, open]);
  const board = useApi(open && can("recovery") ? "/workspace/board" : null);
  const go = (href: string) => { setPalette(false); r.push(href); };
  const needle = q.trim().toLowerCase();
  const hit = (...s: (string | undefined)[]) => !needle || s.some((x) => x && x.toLowerCase().includes(needle));

  const pages: Row[] = useMemo(() => ALL_ITEMS.filter((i) => allowed(i.scope, can) && hit(t(i.label), i.label, i.keywords, t(i.group))).map((i) => ({ id: i.href, label: t(i.label), sub: t(i.group), icon: i.icon, run: () => go(i.href) })), [needle, lang, can]); // eslint-disable-line react-hooks/exhaustive-deps
  const decisions: Row[] = useMemo(() => !board.data ? [] : board.data.lanes.flatMap((l: any) => l.cards.map((c: any) => ({ c, lane: l.label }))).filter(({ c }: any) => needle.length >= 2 && hit(c.title, c.product_id, c.rec_key)).slice(0, 6)
    .map(({ c, lane }: any) => ({ id: c.rec_key, label: c.title, sub: `${t(lane)} · ${egp(c.value_egp)} (${t("estimate")})`, icon: SquareKanban, run: () => go(`/war-room?open=${encodeURIComponent(c.rec_key)}`) })), [board.data, needle]); // eslint-disable-line react-hooks/exhaustive-deps
  const records: Row[] = remote.map((x, i) => ({ id: `${x.type}:${x.id}:${i}`, label: x.label, sub: x.sub, tag: t(x.type), run: () => go(x.url) }));
  const dark = resolveTheme(mode) === "dark";
  const actions: Row[] = [
    { id: "a-theme", label: dark ? t("Switch to light mode") : t("Switch to dark mode"), icon: dark ? Sun : Moon, run: () => { setMode(dark ? "light" : "dark"); setPalette(false); } },
    { id: "a-lang", label: lang === "ar" ? "Switch to English" : "التبديل إلى العربية", icon: Languages, run: () => { setLang(lang === "ar" ? "en" : "ar"); setPalette(false); } },
    { id: "a-side", label: t("Collapse or expand the sidebar"), icon: PanelLeft, run: () => { toggleCollapsed(); setPalette(false); } },
    ...(can("export") && can("executive") ? [{ id: "a-pdf", label: t("Download executive summary (PDF)"), icon: Download, run: () => { setPalette(false); download("/export/executive-summary?format=pdf", "merch-brain-summary.pdf").catch(() => {}); } }] : []),
    { id: "a-out", label: t("Sign out"), icon: LogOut, run: () => { setPalette(false); logout(); } },
  ].filter((a) => hit(a.label, a.id));

  const item = (x: Row) => <Command.Item key={x.id} value={x.id} onSelect={x.run}>{x.icon ? <x.icon className="h-4 w-4 shrink-0 text-slate-500" /> : null}
    <span className="min-w-0 flex-1"><span className="block truncate">{x.label}</span>{x.sub && <span className="block truncate text-xs text-slate-500">{x.sub}</span>}</span>
    {x.tag && <span className="rounded bg-sunken px-1.5 py-0.5 text-[11px] text-slate-500">{x.tag}</span>}</Command.Item>;
  if (!open) return null;
  return <Command.Dialog open={open} onOpenChange={setPalette} label={t("Command palette")} shouldFilter={false} loop
    overlayClassName="fixed inset-0 z-[80] bg-black/55 animate-fade-in" contentClassName="fixed left-1/2 top-[12vh] z-[81] w-[min(94vw,40rem)] -translate-x-1/2 animate-pop-in overflow-hidden rounded-2xl border border-line bg-raised shadow-pop">
    <div className="flex items-center gap-3 border-b border-line px-4"><Search className="h-4 w-4 text-slate-400" />
      <Command.Input value={q} onValueChange={setQ} placeholder={t("Jump to a page, product, invoice or decision…")} className="h-12 flex-1" aria-label={t("Search")} /><kbd className="hidden rounded border border-line px-1.5 py-0.5 text-[11px] text-slate-500 sm:block">Esc</kbd></div>
    <Command.List>
      <Command.Empty>{busy ? t("Searching…") : t("No match. Try a product name, SKU, invoice number or page.")}</Command.Empty>
      {!!pages.length && <Command.Group heading={t("Pages")}>{pages.slice(0, needle ? 8 : 12).map(item)}</Command.Group>}
      {!!decisions.length && <Command.Group heading={t("Decisions")}>{decisions.map(item)}</Command.Group>}
      {!!records.length && <Command.Group heading={t("Records")}>{records.map(item)}</Command.Group>}
      {!!actions.length && <Command.Group heading={t("Actions")}>{actions.map(item)}</Command.Group>}
    </Command.List>
    <div className="flex items-center gap-4 border-t border-line px-4 py-2 text-[11px] text-slate-500"><span className="inline-flex items-center gap-1"><CornerDownLeft className="h-3 w-3" />{t("open")}</span><span>↑↓ {t("navigate")}</span><span className="ms-auto">{t("Approvals are made in the War Room, never from here.")}</span></div>
  </Command.Dialog>;
}
