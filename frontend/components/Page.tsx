"use client";
import { useEffect } from "react";
import { Freshness } from "./Freshness";
import { Card } from "./ui/primitives";
import { useI18n } from "@/lib/i18n";

/** `title`/`sub` are English keys and are translated here. Updates document.title on navigation. */
export const Page = ({
  title,
  sub,
  fresh,
  children,
  right,
}: {
  title: string;
  sub?: string;
  fresh?: any;
  children: React.ReactNode;
  right?: React.ReactNode;
}) => {
  const { t } = useI18n();

  useEffect(() => {
    if (title && typeof document !== "undefined") {
      document.title = `${t(title)} · BUSINESS GATE`;
    }
  }, [title, t]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t(title)}</h1>
          {sub && <p className="text-slate-500">{t(sub)}</p>}
          <div className="mt-1.5">
            <Freshness f={fresh} />
          </div>
        </div>
        {right}
      </div>
      {children}
    </div>
  );
};

export const Panel = ({
  title,
  hint,
  children,
  className,
}: {
  title: string;
  hint?: string;
  children: React.ReactNode;
  className?: string;
}) => {
  const { t } = useI18n();
  return (
    <Card className={`p-5 ${className || ""}`}>
      <div className="mb-3">
        <h3 className="font-semibold">{t(title)}</h3>
        {hint && <p className="text-xs text-slate-500">{t(hint)}</p>}
      </div>
      {children}
    </Card>
  );
};

export const Stat = ({
  label,
  value,
  tone,
}: {
  label: string;
  value: React.ReactNode;
  tone?: string;
}) => {
  const { t } = useI18n();
  return (
    <Card className="p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{t(label)}</p>
      <p className={`mt-1 text-2xl font-semibold ${tone || ""}`}>{value}</p>
    </Card>
  );
};
