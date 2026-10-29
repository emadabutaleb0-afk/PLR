"use client";
import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { useTheme, resolveTheme } from "@/lib/theme";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/** Quick 1-click toggle between Light and Dark mode for the top header. */
export function ThemeSwitch({ className }: { className?: string }) {
  const { t } = useI18n();
  const { mode, setMode } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div
        className={cn(
          "inline-flex h-9 w-9 items-center justify-center rounded-xl border border-line bg-surface text-slate-500",
          className
        )}
      />
    );
  }

  const isDark = resolveTheme(mode) === "dark";

  const toggle = () => {
    setMode(isDark ? "light" : "dark");
  };

  const label = isDark ? t("Switch to light mode") : t("Switch to dark mode");

  return (
    <button
      type="button"
      onClick={toggle}
      title={label}
      aria-label={label}
      className={cn(
        "inline-flex h-9 w-9 items-center justify-center rounded-xl border border-line bg-surface text-slate-600 transition-colors hover:bg-sunken hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
        className
      )}
    >
      {isDark ? (
        <Sun className="h-4 w-4 text-amber-400 transition-transform hover:rotate-45" />
      ) : (
        <Moon className="h-4 w-4 text-slate-600 transition-transform hover:-rotate-12" />
      )}
    </button>
  );
}
