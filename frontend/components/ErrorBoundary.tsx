"use client";
import { Component, ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { Button } from "./ui/primitives";

function Fallback({ onReset }: { onReset: () => void }) {
  const { t } = useI18n();
  return <div role="alert" className="mx-auto my-16 max-w-md rounded-2xl border border-rose-200 bg-surface p-8 text-center shadow-card"><AlertTriangle className="mx-auto h-8 w-8 text-rose-400" />
    <h2 className="mt-3 text-lg font-semibold">{t("This screen hit an unexpected error")}</h2><p className="mt-1 text-sm text-slate-500">{t("Your data and decisions are not affected. Try again, or open another page.")}</p>
    <Button className="mt-4" variant="outline" onClick={onReset}>{t("Try again")}</Button></div>;
}
/** Catches render errors of one screen so the shell stays usable. Logs only the error class, never props or business data. */
export class ErrorBoundary extends Component<{ children: ReactNode; resetKey?: string }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(e: Error) { console.error("UI render error:", e.name); }
  componentDidUpdate(p: { resetKey?: string }) { if (p.resetKey !== this.props.resetKey && this.state.failed) this.setState({ failed: false }); }
  render() { return this.state.failed ? <Fallback onReset={() => this.setState({ failed: false })} /> : this.props.children; }
}
