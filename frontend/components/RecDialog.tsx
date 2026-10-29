"use client";
import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { X, Check, Clock, Ban } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { Badge, Button, Textarea } from "./ui/primitives";
import { egp } from "@/lib/format";

export function RecDialog({ rec, onClose }: { rec: any; onClose: () => void }) {
  const { can } = useAuth();
  const { t } = useI18n();
  const qc = useQueryClient();
  const [comment, setComment] = useState("");
  const [err, setErr] = useState("");
  const [pendingAction, setPendingAction] = useState<string | null>(null);

  useEffect(() => {
    const f = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", f);
    return () => document.removeEventListener("keydown", f);
  }, [onClose]);

  const m = useMutation({
    mutationFn: (decision: string) => {
      setPendingAction(decision);
      return api(`/recommendations/${encodeURIComponent(rec.rec_key).replace(/%3A/g, ":")}/feedback`, {
        method: "POST",
        body: JSON.stringify({ decision, comment: comment || null }),
      });
    },
    onSuccess: () => {
      qc.invalidateQueries();
      onClose();
    },
    onError: (e: any) => {
      setErr(e.message);
      setPendingAction(null);
    },
  });

  const ev = rec.evidence || {};

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4 animate-fade-in"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="rec-dialog-title"
    >
      <div
        className="max-h-[90vh] w-full max-w-2xl overflow-auto rounded-2xl bg-surface p-6 shadow-2xl animate-pop-in border border-line"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <Badge kind={rec.urgency}>{t(rec.urgency)}</Badge>
            <h2 id="rec-dialog-title" className="mt-2 text-xl font-semibold text-slate-900">
              {rec.title}
            </h2>
          </div>
          <button
            onClick={onClose}
            aria-label={t("Close")}
            className="rounded-lg p-1 text-slate-400 hover:bg-sunken hover:text-slate-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <section className="mt-5 space-y-4 text-sm">
          <div>
            <h4 className="font-semibold text-slate-500">{t("What happened")}</h4>
            <p className="mt-1 text-slate-800">{rec.problem}</p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-500">{t("Why this was flagged")}</h4>
            <ul className="mt-1 list-disc space-y-1 ps-5 text-slate-700">
              {rec.why?.map((w: string, i: number) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </div>
          <div className="rounded-xl border border-brand-200/60 bg-brand-50 p-4">
            <h4 className="font-semibold text-brand-700">{t("Recommended action")}</h4>
            <p className="mt-1 text-base font-medium text-brand-900">{rec.action}</p>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-xl border border-line bg-emerald-50 p-3">
              <p className="text-xs text-slate-500">{t("Expected impact")}</p>
              <p className="mt-0.5 font-semibold text-emerald-700">{egp(rec.estimated_value_egp)}</p>
            </div>
            <div className="rounded-xl border border-line bg-sunken p-3">
              <p className="text-xs text-slate-500">{t("Confidence")}</p>
              <p className="mt-0.5 font-semibold text-slate-800">
                {Math.round(rec.confidence * 100)}%
              </p>
            </div>
            <div className="rounded-xl border border-line bg-sunken p-3">
              <p className="text-xs text-slate-500">{t("Department")}</p>
              <p className="mt-0.5 font-semibold text-slate-800">{t(rec.department)}</p>
            </div>
          </div>
          {rec.is_estimate && (
            <p className="text-xs text-slate-500">
              {t("This is an estimate derived from your data.")}
              {ev.basis ? ` (${ev.basis})` : ""}{" "}
              {t("Record the real outcome later so the platform can show realised value.")}
            </p>
          )}
          {ev.assumption && (
            <p className="text-xs text-amber-700">
              {t("Assumption")}: {ev.assumption}
            </p>
          )}
        </section>

        {can("decide") && (
          <div className="mt-5 space-y-3 border-t border-line pt-4">
            <Textarea
              rows={2}
              placeholder={t("Add a comment (optional)")}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
            {err && <p className="text-sm text-rose-600">{err}</p>}
            <div className="flex flex-wrap gap-2">
              <Button
                variant="success"
                disabled={m.isPending}
                loading={m.isPending && pendingAction === "ACCEPT"}
                onClick={() => m.mutate("ACCEPT")}
              >
                {!m.isPending && <Check className="h-4 w-4" />}
                {t("Accept")}
              </Button>
              <Button
                variant="outline"
                disabled={m.isPending}
                loading={m.isPending && pendingAction === "DEFER"}
                onClick={() => m.mutate("DEFER")}
              >
                {!m.isPending && <Clock className="h-4 w-4" />}
                {t("Defer")}
              </Button>
              <Button
                variant="outline"
                disabled={m.isPending}
                loading={m.isPending && pendingAction === "REJECT"}
                onClick={() => m.mutate("REJECT")}
              >
                {!m.isPending && <Ban className="h-4 w-4" />}
                {t("Reject")}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
