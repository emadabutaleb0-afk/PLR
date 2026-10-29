import "@fontsource-variable/inter";
import "@fontsource/ibm-plex-sans-arabic/400.css";
import "@fontsource/ibm-plex-sans-arabic/500.css";
import "@fontsource/ibm-plex-sans-arabic/600.css";
import "@fontsource/ibm-plex-sans-arabic/700.css";
import "./globals.css";
import type { Metadata, Viewport } from "next";
import Providers from "./providers";
export const metadata: Metadata = { title: "BUSINESS GATE · Commercial Decision & Profit Intelligence", description: "AI Commercial Decision & Profit Recovery Engine" };
export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: [{ media: "(prefers-color-scheme: light)", color: "#F8FAFC" }, { media: "(prefers-color-scheme: dark)", color: "#0B0F19" }] };
// Runs before first paint: language + direction (no left-to-right flash for Arabic) and the colour theme (no white flash in dark mode).
const PRE = `try{var d=document.documentElement,l=localStorage.getItem("mb_lang");if(!l)l=(navigator.language||"").toLowerCase().indexOf("ar")===0?"ar":"en";d.lang=l;d.dir=l==="ar"?"rtl":"ltr";var m=localStorage.getItem("mb_theme")||"system";var t=m==="system"?(window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"):m;d.setAttribute("data-theme",t)}catch(e){}`;
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en" dir="ltr" data-theme="light" suppressHydrationWarning><head><script dangerouslySetInnerHTML={{ __html: PRE }} /></head>
    <body className="font-sans antialiased"><a href="#main" className="skip-link">Skip to content</a><Providers>{children}</Providers></body></html>;
}
