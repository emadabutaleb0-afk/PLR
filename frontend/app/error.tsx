"use client";
import { useI18n } from "@/lib/i18n";
import { Button, Card } from "@/components/ui/primitives";
export default function GlobalError({ error, reset }: { error: Error; reset: () => void }) {
  const { t } = useI18n();
  return <div className="grid min-h-screen place-items-center p-4"><Card className="max-w-md space-y-3 p-8 text-center"><h2 className="text-lg font-semibold">{t("Something went wrong")}</h2><p className="text-sm text-slate-500">{t("The page hit an unexpected problem. Your data is safe.")}</p><div className="flex justify-center gap-2"><Button onClick={reset}>{t("Try again")}</Button><Button variant="outline" onClick={() => (window.location.href = "/")}>{t("Go to Today")}</Button></div></Card></div>;
}
