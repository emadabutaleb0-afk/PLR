"use client";
import Link from "next/link";
import { useI18n } from "@/lib/i18n";
export default function NotFound() {
  const { t } = useI18n();
  return <div className="grid min-h-screen place-items-center p-4 text-center"><div><p className="text-5xl font-bold text-slate-300">404</p><p className="mt-2 font-medium">{t("This page does not exist")}</p><Link href="/" className="mt-3 inline-block text-brand-600 underline">{t("Go to Today")}</Link></div></div>;
}
