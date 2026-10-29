"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState, ReactNode } from "react";
import { useTheme } from "@/lib/theme";
import { useWorkspace } from "@/lib/workspace";
import { AuthProvider } from "@/lib/auth";
import { I18nProvider } from "@/lib/i18n";
import { CompanyProvider } from "@/lib/company";
export default function Providers({ children }: { children: ReactNode }) {
  const [qc] = useState(() => new QueryClient({ defaultOptions: { queries: { staleTime: 60_000, retry: (n, e: any) => n < 2 && ![401, 403, 404, 409, 422].includes(e?.status), refetchOnWindowFocus: false } } }));
  useEffect(() => { useTheme.getState().hydrate(); useWorkspace.getState().hydrate(); }, []);
  return <I18nProvider><QueryClientProvider client={qc}><AuthProvider><CompanyProvider>{children}</CompanyProvider></AuthProvider></QueryClientProvider></I18nProvider>;
}
