"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import { useI18n } from "./i18n";
/** Data hook. The language is part of the cache key so switching EN/AR re-fetches server-written sentences in the right language. */
export const useApi = <T = any>(path: string | null, opts: { refetchInterval?: number } = {}) => {
  const { lang } = useI18n();
  return useQuery<T>({ queryKey: [path, lang], queryFn: () => api<T>(path!), enabled: !!path, ...opts });
};
