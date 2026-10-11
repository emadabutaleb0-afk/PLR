"use client";
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { api, tokens } from "./api";
export type User = { id: number; email: string; full_name: string; role: string; scopes: string[]; allowed_locations: string[] | null };
const Ctx = createContext<{ user: User | null; loading: boolean; login: (e: string, p: string) => Promise<void>; logout: () => void; can: (s: string) => boolean }>(null as any);
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null); const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!tokens.get()) { setLoading(false); return; }
    api("/auth/me").then(setUser).catch(() => tokens.clear()).finally(() => setLoading(false));
  }, []);
  const login = async (email: string, password: string) => { const r = await api("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }); tokens.set(r); setUser(r.user); };
  const logout = () => { tokens.clear(); setUser(null); window.location.href = "/login"; };
  const can = (s: string) => !!user?.scopes.includes(s);
  return <Ctx.Provider value={{ user, loading, login, logout, can }}>{children}</Ctx.Provider>;
}
export const useAuth = () => useContext(Ctx);
