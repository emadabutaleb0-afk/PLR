# SHARNOUBY MERCH BRAIN
### ابدأ من هنا / Quick start

**ويندوز:** ثبّت Python 3.11+ و Node.js 20+ ثم اضغط مرتين على `run-windows.bat`. أول مرة بياخد عدة دقائق (تثبيت + بناء)، وبعدها بيفتح المتصفح على http://localhost:3000.
**Linux / macOS:** `./run.sh`

* **الدخول:** البريد وكلمة المرور من ملف `.env` (`BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD`). الافتراضي: `ceo@company.local` / `MyLogin#2026`. غيّر كلمة المرور من *My account*.
* **البيانات:** ملفات الـ CSV في `data/private`. أول تشغيل بيحمّلها **تلقائيًا** (حوالي 30 ثانية) وبتظهر شاشة تقدّم. التحديث بعد كده من *Data Health → Refresh data*.
* **اللغة:** زر **العربية / English** أعلى كل صفحة وفي صفحة الدخول (الاتجاه RTL تلقائي، والاختيار بيتحفظ).
* **المستخدمون:** من *Users & Access* (للـ CEO) تضيف أي عدد من الناس وتحدد دور كل واحد (مدير فرع يشوف فرعه بس، التسويق بدون تكاليف… إلخ)، وتوقف الحساب أو تعيد كلمة المرور.
* لو فتحت التطبيق وملقتش ملفات: انسخ الـ CSV في `data/private` واضغط Retry.

---

English quick start: install Python 3.11+ and Node 20+, run `run-windows.bat` (or `./run.sh`), open http://localhost:3000, sign in with the CEO account from `.env`. The first start loads the company CSVs from `data/private` automatically.

---

# SHARNOUBY MERCH BRAIN
### Fashion Retail Decision Intelligence Platform

A decision-and-execution layer that sits on top of El-Sharnouby's operational data. It does not show "here is your inventory" — it says *which* product is about to run out where, *what* to move or discount, *how much money* is at stake, *how confident* the system is, and then tracks whether the decision actually made money.

> **100% on-premise. No LLM. No external AI API. No data leaves the company network.**

---

## 1. The business problem
Merchandising, production, procurement, quality and marketing each look at their own report. Nobody sees that Marketing is paying to send customers to a product that is out of stock, that a supplier's late deliveries are quietly costing more than its price advantage, or that two locations hold the same product with 4 days and 90 days of cover. Dashboards describe; they do not decide, rank, assign or measure.

## 2. Why dashboards are not enough
| Traditional dashboard | MERCH BRAIN |
|---|---|
| "Here is your inventory." | "Location A will run short of this product before new stock can arrive. Location B has surplus. Move N units. Estimated profit protected: EGP X (estimate, confidence 65%)." |
| Hundreds of charts and alerts | **One** ranked list, de-duplicated, capped alerts |
| No owner, no follow-up | Accept / Reject / Defer → Action Center → recorded outcome → **Value Realization** |

## 3. The solution (what is built)
* **Data pipeline**: drop updated CSVs in a folder → validate → quarantine bad rows → load PostgreSQL → recompute features → ML → 12 decision engines → ranked recommendations.
* **12 decision engines** (explainable, EGP-quantified, estimates clearly labelled): Product Action, Dead-Stock Rescue, Size-Curve, Markdown, Campaign↔Inventory Collision, Margin Erosion, Supplier True Cost, Quality Impact, Recovery Priority, Lost Sales, Inventory Productivity, Product Strategy.
* **Execution layer**: Alert Center, Action Center (NEW → … → DONE), recommendation feedback loop, Value Realization.
* **Premium web app** written for managers, not data scientists (no AUC / coefficients on any business screen).

## 4. Architecture
```
 company CSVs (read-only mount)                    ┌──────────────┐
        │                                          │  Next.js UI  │  TanStack Query/Table, Tailwind, Recharts
        ▼                                          └──────┬───────┘
 ┌───────────────┐  Celery job   ┌─────────────┐          │ /api/v1 (JWT, RBAC)
 │ Ingestion     │──────────────▶│  Worker     │          ▼
 │ validate      │               │ ML + engines│   ┌──────────────┐     ┌────────┐
 │ quarantine    │               └──────┬──────┘   │  FastAPI     │────▶│ Redis  │ cache, broker
 └──────┬────────┘                      ▼          │  backend     │     └────────┘
        └───────────────────────▶ PostgreSQL ◀─────┴──────────────┘
```
`backend/app/{api,auth,core,db,models,repositories,schemas,services,analytics,intelligence,ml,optimization,ingestion,validation,monitoring,workers,tests}`. Heavy work never runs on a request: the API serves pre-computed snapshots (9–17 ms on the real dataset).

## 5. Data privacy
* No LLM / external API anywhere (`grep -r "openai\|anthropic\|gemini" backend` returns nothing). Models are scikit-style (LightGBM) trained locally and stored in `MODEL_DIRECTORY`.
* `data/private/`, `*.csv`, `*.xlsx`, `*.parquet`, `.env`, `*.db`, `*.sqlite` are git-ignored. Tests use a **synthetic generator** (`app/tests/synth.py`), never company data.
* The company folder is mounted **read-only**. The import endpoint cannot be pointed at arbitrary paths (path comes from `DATA_DIRECTORY` only).
* Audit log stores metadata only (never passwords or raw records). Quarantine API never returns raw cell values.

## 6. Data model
20 CSVs → typed PostgreSQL tables with real PK/FK + indexes (`docs/DATA_MODEL.md`). Only relationships that exist are enforced (Product_Master → Sales/Inventory/Marketing/Quality/Production/Printing/BOM; Materials → BOM/PO; Suppliers → PO; Customers/Locations → Sales; Locations → Inventory). Where no key exists the link is **aggregated and documented** (e.g. Printing machine ↔ Machine_Downtime, BOM→material→supplier→product, Customer_Service by month). FKs are *deferred* so a parent file can be replaced atomically.

## 7. Decision engines
See `docs/ENGINES.md` for formulas, assumptions and limits. Principles: every number derives from the loaded data; every estimate is labelled; every recommendation carries *what happened / why / drivers / action / impact / confidence*; correlation is never presented as causation.

## 8. Machine learning (only where justified)
| Model | Used for | Validation |
|---|---|---|
| LightGBM classifier | Stockout risk (next month) | time-based split, 1-month embargo, compared with the simple cover rule |
| LightGBM classifier | Dead-stock risk (next 3 months) | time-based split, 3-month embargo |
| LightGBM regressors (h=1..3) | Demand forecast | back-test vs seasonal-naive and moving-average; baseline is used if the model does not win |
Margin erosion is **not** modelled with ML (month-to-month product margin change is noise-like); an exact additive decomposition is used instead. Markdown and transfer use real optimisation (SciPy bounded minimisation; PuLP/CBC MIP). Metrics, feature importance, model version, train window and prediction-drift are exposed to analysts at `/api/v1/admin/models`.

## 9. Deployment
```bash
cp .env.example .env            # set POSTGRES_PASSWORD, SECRET_KEY, BOOTSTRAP_ADMIN_PASSWORD
mkdir -p data/private           # copy the 20 company CSVs here (or set COMPANY_DATA_PATH)
docker compose up --build       # frontend :3000, API :8000  (add --profile monitoring for Prometheus/Grafana)
```
Sign in as the bootstrap CEO → **Data Health → Refresh data**. Details, backups and upgrades: `docs/DEPLOYMENT.md`.

## 10. Security
bcrypt password hashing · JWT access (30 min) + refresh (7 d) with token-type enforcement · 7 roles with real RBAC (scope + column + row level) · store managers only see allowed locations · marketing has no procurement/cost access · rate limiting · secure headers · CORS allow-list · structured JSON logs · no stack traces to users · CSV-injection-safe exports · audit trail (login, import, export, recommendation viewed/accepted/rejected).

## 11. API
OpenAPI at `/docs` (disabled in production). Main routes: `/api/v1/executive/{overview,decisions,recovery-opportunities}`, `/products[/{id}[/performance|recommendation|sizes]]`, `/inventory/{health,stockout-risk,dead-stock,transfers,lost-sales,productivity}`, `/marketing/{collisions,performance}`, `/suppliers/{performance,true-cost}`, `/quality/impact`, `/operations/bottlenecks`, `/recovery/priorities`, `/recommendations/{key}/{feedback,outcome}`, `/actions`, `/alerts`, `/value/summary`, `/data/{health,import,validate,runs,quarantine}`, `/jobs/{id}`, `/search`, `/export/{dataset}`, `/admin/{models,audit-logs}`. All lists are server-side paginated/sorted/filtered.

## 12. Business value
Value Realization compares **estimated** vs **realised** value of accepted recommendations (profit recovered, loss avoided, revenue protected). Nothing is assumed realised until a user records the outcome — that is what makes the number credible.

## 13. Screenshots
Not bundled (no browser was available while building). After the first deploy, capture Home, Executive Dashboard, Recovery Priorities, Product page, Value Realization and Data Health into `docs/screenshots/`.

## 14. Development & tests
```bash
cd backend && pip install -r requirements.txt && python -m pytest -q      # 42 tests, synthetic data
TEST_DATABASE_URL=postgresql+psycopg2://... python -m pytest -q           # same suite on PostgreSQL
cd frontend && npm install && npm test && npm run build
```
CI: `.github/workflows/ci.yml`.

## 15. Honest status & limitations
* **Verified here**: full pipeline + API on the 20 provided files (244,827 rows, 0 rejected) on SQLite **and real PostgreSQL 16** (import ≈ 30–50 s); 42 backend tests pass on both; frontend type-checks, builds and passes unit tests; Alembic migration applies on PostgreSQL.
* **Not verified here** (no Docker/Redis in the build sandbox): `docker compose up`, the Celery+Redis path (the same job code also runs in a thread when `CELERY_ENABLED=false`), Prometheus/Grafana provisioning, and a browser walk-through of the UI.
* **The provided CSVs are labelled "Modeled/anonymized training data"** in their `Data_Class` column. The app shows this on Data Health; its figures are demonstrations until real files replace them.
* **Data limits that shape the engines**: `Inventory_History` has no size → current stock by size is *unavailable* (size engine reports sales-mix shifts, not stock-based size stockouts); only 3 stock locations (Store, Online, Wholesale); no transfer cost (configurable, default 0); no price response measurable (assumed lift is configurable and flagged); Customer_Service has no product key (aggregated by month only); purchase-order spend exceeds sales (flagged on Data Health).
* Not implemented: XGBoost models (LightGBM is used), product images (placeholder), feature-level drift (prediction drift only), per-user notification preferences.


## Frontend V5 (premium workspace)
See `docs/FRONTEND_V5.md`: what was built (War Room, Command Map, Time Machine, Investigation, Notification Center, Advanced Analytics, light/dark design system), install commands, the checks that were actually run, and what is not supported.
