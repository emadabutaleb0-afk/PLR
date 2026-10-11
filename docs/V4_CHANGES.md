# V4 changes (phases 1-2 of the plan)

## Phase 1 - trust
- `core/config.py` `production_problems()`; `main.py` refuses to start with `ENVIRONMENT=production` on default/weak SECRET_KEY, admin password, placeholder admin email or wildcard CORS.
- `validation/reconcile.py` + `GET /api/v1/data/reconciliation` (scope `data_health`): cross-file consistency checks. CLI: `python -m app.validation.reconcile <data_dir>`.
  On the supplied 20 files: sales arithmetic, sales-vs-inventory units, QC/production identities and product keys are clean; WARN on inventory roll-forward (2.2% of rows),
  production vs sales units (~3.8x) and purchases vs net sales (~2.1x): different accounting scopes, never net them against each other.
- `tests/test_phase1.py`: guard, reconciliation, full decision journey (view -> approve -> action -> outcome -> value -> audit).

## Phase 2 - cross-department decision optimiser
- `optimization/portfolio.py`: binary MILP (PuLP/CBC, no LLM) choosing one consistent set of recommendations under conflicts, stock, dependencies, cash outlay and department capacity.
- Three plans per refresh: Max Profit, Balanced, Min Risk. Every excluded decision carries a reason. Stored as snapshot `decision_plans`; served at `GET /api/v1/commercial/decision-plans`.
- New settings: `DECISION_BUDGET_EGP` (empty = unconstrained), `MAX_ACTIONS_PER_DEPARTMENT` (default 8, an ASSUMPTION).
- `tests/test_portfolio.py`: conflicts, stock, dependencies, budget, department cap, min-risk threshold, endpoint + permissions.

## Phase 3 - business autopsy
- `intelligence/autopsy.py`, `GET /commercial/autopsy`: exact decomposition of the contribution change (last 90 days vs previous 90) into nine drivers, by company / family / product, reusing the Margin Erosion effects. Always reconciles to the total.
- Evidence chains for the biggest drags: every link is labelled accounting / observed / estimate / association / hypothesis; `causal_claim` is always "not established".
- Automatic warnings, e.g. when most of the movement is factory-side (different scope from the sales ledger).
- On the supplied files contribution rose EGP 577K (199K -> 776K), mainly because production rejects fell by 1.18M: flagged as a lead to check, not a confirmed gain.

## Phase 3 - Business Autopsy
- `intelligence/autopsy.py` + `GET /api/v1/commercial/autopsy`: company-level contribution change (last 90 vs previous 90) split into exact additive drivers, then an evidence chain per driver that hurt profit. Every link is labelled accounting / association / hypothesis; a hypothesis is never stated as a cause.
- `quality_loss`, `rework`, `production_rejects` carry a `scope_warning`: the V3 margin engine deducts factory/QC costs unscaled while factory volumes are ~3.8x the sales ledger. On the supplied files the +290% contribution swing is mostly `production_rejects` (+1.18M) and must NOT be presented as a business result.
- `business_autopsy(mg, leak, disc, ql, sup, ops, cfg, lost=, coll=)` is the adapter used by `post_load.compute_all`.

## Phase 4 - execution and outcome tracking
- `DecisionTracking` (migration 0002): every approval freezes a baseline (what was known, data date, engine estimate). Lifecycle APPROVED -> EXECUTED -> MEASURING -> MEASURED | UNMEASURABLE.
- Approve one decision or a whole plan (`POST /commercial/decision-plans/{max_profit|balanced|min_risk}/approve`). Marking the action In progress / Done (optionally `executed_on`) starts the window (`OUTCOME_WINDOW_DAYS`, default 28).
- `services/outcomes.py`: difference-in-differences against untouched comparable products + a placebo test on every control. A result is `claimable` only if significant, positive and >= 9 controls were usable. Re-measured after every data refresh; `POST /decisions/tracking/measure` runs it on demand.
- Stale-data guard: approvals are refused when the newest business data is older than STALE_DATA_DAYS unless `acknowledge_stale=true` (audited). `BLOCK_STALE_APPROVALS=false` disables it.
- `/value/summary` gets a separate `measured_outcomes` block; the engine's expected value is never mixed into the measured figure.
- Calibration on the real files with 36 FAKE past executions: 5 looked significant (14%) vs ~10% expected by chance, so the method does not invent effects. Decision types with no sales signal (quality, supply, phase-out, capacity) are marked UNMEASURABLE and need a manual outcome.
- Limits: sales-side gross profit only; simultaneous changes are not separated; the supplied data ends 2026-09, so real decisions can only be measured once new data arrives.

## Phase 5 - hardening and screens
- Frontend: **Decision Plans** (3 plans, approve, why-excluded, tracking & outcomes) and **Business Autopsy** pages, EN + AR, in the navigation. Checked in a real browser: no console errors.
- `services/backup.py` (SQLite online backup, integrity check, safe restore keeping `.before-restore`), `ops/restore.sh` (PostgreSQL), `docs/RUNBOOK.md`.
- `tests/test_hardening.py`: a fresh `alembic upgrade head` must match the models; backup/restore round trip; corrupt backup refused.
- A placeholder admin email (`*.local`) is now a startup warning in production, not a blocker (the compose default would otherwise fail on first start).

## Honest results on the supplied (modeled) data
- 202 candidates, only 3 conflicts (EGP ~4k overlap): the binding constraint is department capacity, not conflicts.
- Balanced plan needs ~47% less replenishment cash than Max Profit for ~1.4% less confidence-adjusted value. All values are engine estimates, not realised savings.

## Not done yet
Docker/Redis/Celery end-to-end run (docker is not available in the build environment: compose file only validated with `docker compose config`), load testing, Arabic review of the new strings by a native speaker, a frontend page for the plans, Docker/Redis/Celery end-to-end run.


## Integration notes (frontend)
- Pages `/decisions` (plans, approval, tracking, measuring) and `/autopsy` read the API contracts above. The autopsy payload exposes `delta_egp, contribution_now_egp, contribution_prev_egp, reconciles, warnings[], drivers[] (all drivers), chains[] (drivers that hurt profit, with links[level, statement, source, stage, caveat]), by_family[], worst_products[], legend, notes`.
- Verified on the supplied files: backend tests, `tsc`, `vitest`, `next build`, and both pages loaded in a real browser with no console errors.


## Validation run (production-readiness pass)
- Backend suite 91 tests; `ops/preflight.py` 29 ok / 0 blockers; `docker compose config` valid.
- Real Redis + Celery worker (local processes, no Docker daemon available): `ops/smoke.py --import` 13/13 checks, the import was executed by the worker.
- Browser walkthrough of all 27 routes in EN and AR on the real files: 54/54 clean loads (see `docs/WALKTHROUGH.md`).
- Arabic gaps found by scanning the UI strings against `ar.ts` were filled (decision plans, autopsy); department names are translated in the plans table.
- Acceptance script for the company: `docs/ACCEPTANCE_TEST.md`.
- Not verified: the Docker stack itself, other roles in the browser, mobile layouts, a real user from the company.
