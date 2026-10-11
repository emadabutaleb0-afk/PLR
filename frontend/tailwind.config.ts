import type { Config } from "tailwindcss";

/** Colours are CSS variables (app/theme.css, generated) so one class works in light and dark mode: `text-slate-500`, `bg-emerald-50`, `bg-surface`... */
const v = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;
const scale = (name: string, shades: number[]) => Object.fromEntries(shades.map((s) => [s, v(`${name}-${s}`)]));
const S10 = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900];

export default {
  darkMode: ["selector", '[data-theme="dark"]'],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: { extend: {
    colors: {
      slate: scale("slate", [...S10, 950]),
      emerald: scale("emerald", S10), rose: scale("rose", S10), amber: scale("amber", S10), orange: scale("orange", S10), sky: scale("sky", S10), violet: scale("violet", S10),
      brand: scale("brand", S10),
      canvas: v("canvas"), surface: v("surface"), raised: v("raised"), sunken: v("sunken"), line: { DEFAULT: v("line"), strong: v("line-strong") },
      accent: { DEFAULT: v("accent"), hover: v("accent-hover"), fg: v("accent-fg") },
      // fixed (theme independent): the dark sidebar and brand artwork
      ink: { DEFAULT: "#0B1220", 950: "#070C16", 900: "#0B1220", 800: "#151E2D", 700: "#1B2638", 600: "#25324A" },
    },
    boxShadow: { card: "0 1px 2px rgba(11,18,32,.05), 0 10px 28px -16px rgba(11,18,32,.18)", pop: "0 24px 64px -16px rgba(0,0,0,.45)" },
    fontFamily: {
      sans: ["Inter Variable", "IBM Plex Sans Arabic", "ui-sans-serif", "system-ui", "Segoe UI", "Tahoma", "Noto Sans Arabic", "sans-serif"],
      arabic: ["IBM Plex Sans Arabic", "Inter Variable", "Segoe UI", "Tahoma", "sans-serif"],
    },
    keyframes: {
      "fade-in": { from: { opacity: "0" }, to: { opacity: "1" } },
      "slide-in-end": { from: { transform: "translateX(var(--slide-from, 24px))", opacity: "0" }, to: { transform: "translateX(0)", opacity: "1" } },
      "pop-in": { from: { transform: "translateY(6px) scale(.98)", opacity: "0" }, to: { transform: "translateY(0) scale(1)", opacity: "1" } },
    },
    animation: { "fade-in": "fade-in .16s ease-out", "slide-in-end": "slide-in-end .22s cubic-bezier(.2,.8,.2,1)", "pop-in": "pop-in .16s ease-out" },
  } },
  plugins: [],
} satisfies Config;
