"use client";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, ReactNode } from "react";
import { AR } from "./ar";

export type Lang = "en" | "ar";
export const LANG_KEY = "mb_lang";
/** Module-level mirror of the active language so plain helpers (egp, pct, api headers) can read it without a hook. */
export const i18nState: { lang: Lang } = { lang: "ar" };

const readStored = (): Lang => {
  try {
    const v = localStorage.getItem(LANG_KEY);
    if (v === "ar" || v === "en") return v;
    return "ar";
  } catch { return "ar"; }
};

type Ctx = { lang: Lang; dir: "ltr" | "rtl"; isAr: boolean; setLang: (l: Lang) => void; t: (key: string, vars?: Record<string, string | number>) => string };
const I18n = createContext<Ctx>({ lang: "ar", dir: "rtl", isAr: true, setLang: () => {}, t: (k) => k });

/** Translate a UI string. English text is the key; a missing Arabic entry falls back to the English text (never breaks a screen). */
export const translate = (lang: Lang, key: string, vars?: Record<string, string | number>) => {
  let s = lang === "ar" ? AR[key] ?? key : key;
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(String(v));
  return s;
};

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("ar");
  useEffect(() => { const l = readStored(); i18nState.lang = l; setLangState(l); }, []);
  useEffect(() => {
    i18nState.lang = lang;
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  }, [lang]);
  const setLang = useCallback((l: Lang) => { i18nState.lang = l; try { localStorage.setItem(LANG_KEY, l); } catch {} setLangState(l); }, []);
  const t = useCallback((key: string, vars?: Record<string, string | number>) => translate(lang, key, vars), [lang]);
  const value = useMemo(() => ({ lang, dir: (lang === "ar" ? "rtl" : "ltr") as "ltr" | "rtl", isAr: lang === "ar", setLang, t }), [lang, setLang, t]);
  return <I18n.Provider value={value}>{children}</I18n.Provider>;
}
export const useI18n = () => useContext(I18n);
