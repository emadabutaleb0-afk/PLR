"use client";
import { AlertTriangle, Inbox, WifiOff } from "lucide-react";
import { Button, Skeleton, Card } from "./ui/primitives";
import { useI18n } from "@/lib/i18n";
export const LoadingGrid = ({ n = 4 }: { n?: number }) => <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{Array.from({ length: n }).map((_, i) => <Skeleton key={i} className="h-28" />)}</div>;
export const LoadingBlock = ({ h = "h-64" }: { h?: string }) => <Skeleton className={`w-full ${h}`} />;
export const Empty = ({ title, hint }: { title?: string; hint?: string }) => {
  const { t } = useI18n();
  return <Card className="flex flex-col items-center gap-2 p-10 text-center"><Inbox className="h-8 w-8 text-slate-300" /><p className="font-medium text-slate-700">{t(title || "Nothing here yet")}</p>{hint && <p className="max-w-md text-sm text-slate-500">{t(hint)}</p>}</Card>;
};
export const ErrorState = ({ error, retry }: { error: any; retry?: () => void }) => {
  const { t } = useI18n();
  const net = error?.code === "network" || error?.status === 0;
  const Icon = net ? WifiOff : AlertTriangle;
  return <Card className="flex flex-col items-center gap-3 border-rose-200 p-8 text-center" role="alert"><Icon className="h-8 w-8 text-rose-400" />
    <p className="font-medium text-slate-800">{error?.status === 403 ? t("You do not have access to this area") : net ? t("Cannot reach the server") : t("We could not load this")}</p>
    <p className="max-w-md text-sm text-slate-500">{error?.message || t("Please try again.")}</p>
    {retry && error?.status !== 403 && <Button variant="outline" onClick={retry}>{t("Retry")}</Button>}</Card>;
};
