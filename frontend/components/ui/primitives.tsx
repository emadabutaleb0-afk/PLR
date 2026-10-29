"use client";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import {
  ButtonHTMLAttributes,
  HTMLAttributes,
  InputHTMLAttributes,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
  LabelHTMLAttributes,
  forwardRef,
} from "react";
import { Loader2 } from "lucide-react";

const buttonV = cva(
  "inline-flex items-center justify-center gap-2 rounded-xl text-sm font-medium transition disabled:opacity-50 disabled:pointer-events-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500",
  {
    variants: {
      variant: {
        primary: "bg-accent text-accent-fg hover:bg-accent-hover shadow-sm",
        outline: "border border-line bg-surface hover:bg-sunken text-slate-800",
        ghost: "hover:bg-sunken text-slate-700",
        danger: "bg-rose-600 text-white hover:bg-rose-700",
        success: "bg-emerald-600 text-white hover:bg-emerald-700",
      },
      size: { sm: "h-8 px-3 text-xs", md: "h-10 px-4", icon: "h-9 w-9" },
    },
    defaultVariants: { variant: "primary", size: "md" },
  }
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonV> {
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, loading, disabled, children, ...p }, r) => (
    <button
      ref={r}
      disabled={disabled || loading}
      className={cn(buttonV({ variant, size }), className)}
      {...p}
    >
      {loading && <Loader2 className="h-4 w-4 shrink-0 animate-spin" />}
      {children}
    </button>
  )
);
Button.displayName = "Button";

export const Card = ({ className, ...p }: HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("rounded-2xl border border-line bg-surface shadow-card", className)} {...p} />
);

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...p }, r) => (
    <input
      ref={r}
      className={cn(
        "h-10 w-full rounded-xl border border-line bg-surface px-3 text-sm outline-none transition placeholder:text-slate-400 focus:border-accent focus:ring-2 focus:ring-accent/25",
        className
      )}
      {...p}
    />
  )
);
Input.displayName = "Input";

export const Select = ({ className, ...p }: SelectHTMLAttributes<HTMLSelectElement>) => (
  <select
    className={cn(
      "h-9 rounded-xl border border-line bg-surface px-3 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/25",
      className
    )}
    {...p}
  />
);

const tone: Record<string, string> = {
  CRITICAL: "bg-rose-50 text-rose-700 ring-rose-200",
  HIGH: "bg-orange-50 text-orange-700 ring-orange-200",
  WARNING: "bg-amber-50 text-amber-700 ring-amber-200",
  MEDIUM: "bg-amber-50 text-amber-700 ring-amber-200",
  LOW: "bg-slate-50 text-slate-600 ring-slate-200",
  OPPORTUNITY: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  OK: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  HEALTHY: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  FAILED: "bg-rose-50 text-rose-700 ring-rose-200",
  MISSING: "bg-rose-50 text-rose-700 ring-rose-200",
  UNHEALTHY: "bg-rose-50 text-rose-700 ring-rose-200",
  ATTENTION: "bg-amber-50 text-amber-700 ring-amber-200",
  STALE: "bg-amber-50 text-amber-700 ring-amber-200",
  FRESH: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  ESTIMATE: "bg-amber-50 text-amber-700 ring-amber-200",
  EXPOSURE: "bg-orange-50 text-orange-700 ring-orange-200",
  RECORDED: "bg-slate-100 text-slate-700 ring-slate-200",
  AT_RISK: "bg-rose-50 text-rose-700 ring-rose-200",
  WATCH: "bg-amber-50 text-amber-700 ring-amber-200",
  READY: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  INFO: "bg-brand-50 text-brand-700 ring-brand-100",
  DONE: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  NEW: "bg-brand-50 text-brand-700 ring-brand-100",
  NEUTRAL: "bg-slate-100 text-slate-700 ring-slate-200",
  SUCCESS: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  ERROR: "bg-rose-50 text-rose-700 ring-rose-200",
};

export const Badge = ({
  children,
  kind,
  className,
}: {
  children: React.ReactNode;
  kind?: string;
  className?: string;
}) => (
  <span
    className={cn(
      "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset",
      tone[kind || "INFO"] || tone.INFO,
      className
    )}
  >
    {children}
  </span>
);

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...p }, r) => (
  <textarea
    ref={r}
    className={cn(
      "w-full rounded-xl border border-line bg-surface p-3 text-sm outline-none transition placeholder:text-slate-400 focus:border-accent focus:ring-2 focus:ring-accent/25",
      className
    )}
    {...p}
  />
));
Textarea.displayName = "Textarea";

export const Label = ({ className, ...p }: LabelHTMLAttributes<HTMLLabelElement>) => (
  <label className={cn("mb-1 block text-xs font-medium text-slate-600", className)} {...p} />
);

export const Spinner = ({ className }: { className?: string }) => (
  <Loader2 className={cn("h-4 w-4 animate-spin", className)} />
);

export const Skeleton = ({ className }: { className?: string }) => (
  <div
    className={cn(
      "relative overflow-hidden rounded-xl bg-slate-200/70 before:absolute before:inset-0 before:-translate-x-full before:animate-[shimmer_1.4s_infinite] before:bg-gradient-to-r before:from-transparent before:via-surface/60 before:to-transparent",
      className
    )}
  />
);

export const Progress = ({ value }: { value: number }) => (
  <div className="h-2 w-full overflow-hidden rounded-full bg-sunken border border-line/40">
    <div
      className="h-full rounded-full bg-brand-600 transition-all duration-300"
      style={{ width: `${Math.round(Math.min(Math.max(value, 0), 1) * 100)}%` }}
    />
  </div>
);
