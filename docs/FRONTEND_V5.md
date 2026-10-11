# Frontend V5 — Premium decision workspace

What changed in the web app, how to run it, what was actually tested, and what is **not** built.
Everything below was checked against the running code; where something was not tested it says so.

## 1. What you get

| Area | What it is | Real data it uses |
|---|---|---|
| **Design system** | Midnight navy `#0B1220`, charcoal `#151E2D`, warm off-white `#F8F7F4`, emerald `#10B981`, muted gold `#C5A46D`. Light and dark mode (follows the OS by default, switchable). Tabular numerals for money. Inter (Latin) + IBM Plex Sans Arabic, **self-hosted** (no font request leaves the company network). | — |
| **Shell** | Collapsible sidebar, compact header, breadcrumbs, contextual "Related" links, role-aware navigation, notification bell, user menu (theme, language, sign out), skip-link, mobile drawer. | `/auth/me` scopes, `/workspace/notifications` |
| **Command palette** (Ctrl/Cmd+K) | Pages (only the ones your role may open), products / invoices / suppliers / campaigns (existing `/search`), open decisions, and safe actions (theme, language, sidebar, PDF summary, sign out). **It never approves anything.** | `/search`, `/workspace/board` |
| **Decision War Room** `/war-room` | Lanes: Awaiting decision → Deferred → Approved · not started → In progress → Executed · measuring → Measured → Rejected. Each lane shows its 40 most urgent / highest-value cards; the lane header shows the true total. Search, department and urgency filters, compare up to several decisions side by side, drag-and-drop with dnd-kit. Decision drawer: what happened, recommended action, expected impact (always tagged *Estimate*), confidence, downside, evidence, links to Product 360 / Investigate / Map, tracking result, full activity history. | `/workspace/board`, `/workspace/decisions/history`, existing `/recommendations/{key}/feedback` and `/actions/{id}` |
| **Command Map** `/map` | React Flow graph of real relationships only: product–location (stock/sales rows), product–material (bill of materials), material–supplier (purchase orders), decision–product. Click a node for its figures, its connections and links to the related pages. Open decisions are revealed per selected product (82 at once is unreadable). | `/workspace/network` |
| **Product 360°** `/products/{id}` | The existing product page (Performance, Inventory, Sizes, Locations, Marketing, Quality, Production, Returns, Recommendations) plus a **Supply chain** tab (materials → suppliers) and a **History** tab (decision history), fed by the new context endpoint. Related-page links (Investigate, Time Machine, Show on map) sit in the header. | `/workspace/products/{id}/context` + existing product API |
| **Business Time Machine** `/time-machine` | Monthly sales, inventory and production history rebuilt from the raw tables, date range, product and location filters, click a month for before/after, event markers that were actually recorded (campaigns, approvals, executions, measured outcomes, data refreshes). Metrics with no history are listed as unavailable. | `/workspace/timeline`, `/workspace/scope-options` |
| **Investigation** `/investigate` | Two linked panels (resizable split) for one product: sales vs stock, returns, supplier and production context. Product, location and selected month are shared between panels. Layouts can be saved. | `/workspace/timeline`, `/workspace/products/{id}/context` |
| **Notification Center** `/notifications` + bell | Pending approvals, alerts, data-quality issues, open actions "open for N days", measured outcomes; each links to its entity. Virtualised list. Counts are the real number of rows the API returns for your role (the bell shows `99+` above 99). | `/workspace/notifications` |
| **Advanced Analytics** `/analytics` | Catalogue of approved reporting views (CSV/XLSX through the existing audited export endpoints) and an honest Power BI readiness checklist. | `/workspace/reports`, `/export/*` |

Existing 27 pages were **kept** and themed (light/dark) without changing their logic; their chart colours now follow the theme.

## 2. Backend additions (read-only)
`backend/app/api/workspace.py` adds `/api/v1/workspace/{notifications, network, scope-options, timeline, products/{id}/context, board, decisions/history, reports}`.
They only **read**. A test (`test_workspace_is_read_only`) asserts they change nothing. Role scopes, cost-field stripping and the store-manager location restriction are applied exactly as in the existing APIs. Arabic for the server-written sentences was added to `app/core/i18n_ar.py`.
No existing endpoint, model, engine or migration was changed.

## 3. Install and run
```bash
cd frontend
npm install            # new packages: @xyflow/react, cmdk, zustand, @dnd-kit/core, @dnd-kit/utilities,
                       #   @tanstack/react-virtual, @fontsource-variable/inter, @fontsource/ibm-plex-sans-arabic
                       # dev: eslint, eslint-config-next, jsdom, @testing-library/react, @testing-library/user-event
npm run dev            # or: npm run build && npm start
npm run typecheck      # tsc --noEmit
npx next lint          # ESLint
npm test               # vitest (unit + component tests)
```
Backend is unchanged: `run.sh` / `run-windows.bat` / `docker compose up` as before. Regenerate colours after editing the palette with `node scripts/gen-theme.mjs` (it refuses to write colours that fail a WCAG contrast check).

## 4. What was actually run (2026-10-11, this machine)

| Check | Result |
|---|---|
| `tsc --noEmit` | no errors |
| `next lint` | no warnings or errors |
| `next build` | compiled, 38 routes generated |
| Frontend tests (vitest) | **21 / 21 passed** (4 files): approval needs an explicit confirmation and sends exactly one request; Cancel/Esc send nothing; a server refusal is shown, never reported as success; a role without `decide` has no approve buttons; drag rules never offer an approval from closed lanes; role-aware navigation; breadcrumbs |
| Backend tests (pytest) | **100 / 100 passed** (including 9 new workspace tests) |
| Browser walkthrough (real Chromium) | 226 page loads: CEO (EN light, AR dark RTL, EN dark, tablet 820 px, mobile 390 px), Store, Marketing, Analyst and Production managers. **No console errors, no runtime exceptions, no horizontal overflow.** The only HTTP 403s were a role opening, by URL, a page it is not allowed to see; those pages show the "no access" message |
| Interactive checks (14) | Ctrl+K opens, finds and navigates; War Room drawer opens; Approve opens a confirmation and **no request is sent**; Esc closes the confirmation first, then the drawer; first Tab reaches the skip-link; `<main>` landmark present; map renders 42 readable nodes and the details panel works |
| Arabic | every UI string used in the new code has an Arabic entry (scan: 0 missing, except the intentionally bilingual language button); `dir="rtl"` verified on all Arabic loads |

Screenshots: `docs/screenshots/premium/`.

### What this does **not** prove
- No automated accessibility audit (axe/Lighthouse) was run. Keyboard paths, focus trap/return, landmarks, reduced-motion and the 44-pair colour-contrast gate were checked; screen-reader behaviour was not.
- The approve → action item → tracking write path was tested in unit tests with a mocked API and by the existing backend tests, **not** by clicking Approve in the browser (so the demo database stays untouched).
- Drag-and-drop was unit-tested (rules) but not exercised with a mouse in the browser.
- Firefox, Safari and real phones/tablets were not used (Chromium with phone/tablet viewports only).
- The Docker stack has never been started here (no Docker daemon).
- Data is modelled/anonymised: all values on open decisions are **estimates**, and no real decision has been measured yet.

## 5. Not supported / dependencies
- **Power BI embedding is not implemented.** Power BI Desktop or Report Server can read the CSV/XLSX exports or the API *inside the company network*. Embedding needs a Power BI Report Server or licensed capacity, a service account and a security model: IT decisions. Nothing is sent to any cloud service.
- **Time Machine cannot show what the system recommended in the past**: recommendation and alert snapshots are stored latest-only. It shows what happened (sales, stock, production) and recorded events only. Making this possible needs a snapshot history table (backend change).
- **Business units are shown without connections** on the map: the data has no link between them and locations, products or suppliers.
- **"Delayed" actions** means open for 7+ days: actions have no due date in the data model.
- **Saved investigation layouts are per browser** (localStorage). Shared team layouts need a server table.
- **Business-facing charts stay on Recharts**, not ECharts, and **Framer Motion is not used**: CSS transitions only, disabled under reduced-motion. Cross-filtering is limited to the linked panels in Investigation and the month selection in the Time Machine.
- Engine-generated titles and evidence (e.g. "Replenish: …") are translated by templates; a sentence with no template stays in English rather than breaking the screen. Product, location and supplier names are never translated.
- Notification read/unread state is not stored per user (the API has none); the bell shows what currently needs attention.

## 6. Safety properties kept
- Approving, deferring or rejecting is done **only** in the decision drawer, after a confirmation dialog, through the existing endpoint. The server re-checks the role, the stale-data guard and writes the audit log. Dragging a card only opens that same confirmation.
- The command palette has no approval or data-changing command.
- No business value is hard-coded; values from engines are labelled *Estimate*, measured effects *Measured*.
- Tokens stay in `localStorage` as before; no business data is written to logs or storage (only layout names and UI state).
