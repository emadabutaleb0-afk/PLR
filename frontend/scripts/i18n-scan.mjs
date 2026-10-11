// Lists English UI strings that have no Arabic entry in lib/ar.ts. Run: node scripts/i18n-scan.mjs [--all]
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
const walk = (d) => readdirSync(d).flatMap((f) => { const p = join(d, f); return statSync(p).isDirectory() ? (f === "node_modules" || f === ".next" ? [] : walk(p)) : /\.(tsx?|ts)$/.test(f) ? [p] : []; });
const ar = readFileSync("lib/ar.ts", "utf8");
const have = new Set([...ar.matchAll(/"((?:[^"\\]|\\.)*)"\s*:/g)].map((m) => m[1].replace(/\\"/g, '"')));
const found = new Map();
const add = (s, f) => { s = s.replace(/\\"/g, '"'); if (s.length < 2 || !/[A-Za-z]{2}/.test(s) || /^[a-z_]+$/.test(s) || /^[\w./:?=&#-]+$/.test(s) && !/[A-Z]/.test(s[0])) return; if (!found.has(s)) found.set(s, f); };
for (const f of walk(".").filter((x) => !x.startsWith("./lib/ar.ts") && !x.includes(".test.") && !x.startsWith("./scripts"))) {
  const src = readFileSync(f, "utf8");
  for (const m of src.matchAll(/\bt\(\s*"((?:[^"\\]|\\.)*)"/g)) add(m[1], f);
  for (const m of src.matchAll(/\b(?:title|sub|hint|label|placeholder|aria-label)=\s*"((?:[^"\\]|\\.)*)"/g)) add(m[1], f);
  for (const m of src.matchAll(/\bt\(\s*`([^`$]*)`\s*[,)]/g)) add(m[1], f);
  // label/title/text object properties and string arrays that are passed through t() later
  for (const m of src.matchAll(/\b(?:label|title|text|kind|help|reason)\s*:\s*"((?:[^"\\]|\\.)*)"/g)) add(m[1], f);
}
const missing = [...found].filter(([s]) => !have.has(s));
for (const [s, f] of missing) console.log(`${f}\t${s}`);
console.error(`\n${missing.length} string(s) without an Arabic entry (of ${found.size} scanned).`);
