"use client";
import { create } from "zustand";

export type ThemeMode = "light" | "dark" | "system";
export const THEME_KEY = "mb_theme";

const safe = <T,>(f: () => T, d: T): T => { try { return f(); } catch { return d; } };
export const resolveTheme = (m: ThemeMode): "light" | "dark" =>
  m === "system" ? (typeof window !== "undefined" && window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light") : m;

/** Writes the resolved theme to <html data-theme>; the inline script in app/layout.tsx does the same before first paint. */
export const applyTheme = (m: ThemeMode) => {
  if (typeof document === "undefined") return;
  document.documentElement.setAttribute("data-theme", resolveTheme(m));
};

type S = { mode: ThemeMode; setMode: (m: ThemeMode) => void; hydrate: () => void };
export const useTheme = create<S>((set) => ({
  mode: "system",
  setMode: (mode) => { safe(() => localStorage.setItem(THEME_KEY, mode), undefined); applyTheme(mode); set({ mode }); },
  hydrate: () => {
    const v = safe(() => localStorage.getItem(THEME_KEY), null);
    const mode: ThemeMode = v === "light" || v === "dark" || v === "system" ? v : "system";
    applyTheme(mode); set({ mode });
  },
}));
