# SHARNOUBY MERCH BRAIN - operations runbook

## Start / stop
- Local (one PC): `run-windows.bat` or `./run.sh`. Data lives in `backend/merchbrain.db` (SQLite); company CSVs in `data/private/`.
- Server (Docker): `docker compose up -d --build`. Needs `.env` with `POSTGRES_PASSWORD`, `SECRET_KEY` (32+ chars), `BOOTSTRAP_ADMIN_PASSWORD` (12+ chars), and a real `BOOTSTRAP_ADMIN_EMAIL`.
- With `ENVIRONMENT=production` the app refuses to start on a default or weak SECRET_KEY / admin password or a wildcard CORS. The error names what to fix.

## Daily use
1. Put the new CSV exports in `data/private/` (same file names), then press **Refresh data** (Data Health).
2. Check **Data Health** and `GET /api/v1/data/reconciliation`: files that disagree are listed, with their numbers. Do not quote a headline number whose check is WARN without the caveat.
3. **Decision Plans**: pick a plan, approve it. Each decision becomes an action item for its department. Nothing is executed by the system.
4. When a department starts the work, mark the action **In progress** (set the real date if it started earlier). The before/after window (28 days, `OUTCOME_WINDOW_DAYS`) starts then.
5. After each refresh the system measures every decision whose window is complete. **Tracking & outcomes** shows expected value and measured effect separately; only effects that stand out from comparable untouched products are claimable.
6. Quality, supply, phase-out and capacity decisions cannot be measured from sales: record their outcome manually on the recommendation.

## Backup and restore
- Docker/PostgreSQL: nightly `ops/backup.sh` (cron, keeps 14 days). Restore: `ops/restore.sh backups/<file>.dump` (takes a safety dump first, then replaces the database).
- Local SQLite: `python -m app.services.backup backup backend/merchbrain.db backups/merchbrain.db` (safe while running). Restore with the app stopped: `python -m app.services.backup restore backups/merchbrain.db backend/merchbrain.db` (the replaced file is kept as `.before-restore`; a backup that fails its integrity check is refused).
- Test a restore once per quarter on a copy. A backup you have never restored is not a backup.

## Upgrades
- `alembic upgrade head` (Docker does this on start). `tests/test_hardening.py` fails if the models and migrations drift apart.
- After upgrading, press **Refresh data** once so the new analytics (plans, autopsy) are computed.

## Settings you should confirm with management (they are assumptions, not company facts)
`MAX_ACTIONS_PER_DEPARTMENT` (8), `DECISION_BUDGET_EGP` (empty = no cash cap), `TRANSFER_COST_PER_UNIT_EGP` (0), `MARGIN_FLOOR_PCT`, `CAPITAL_COST_ANNUAL_PCT`, `ASSUMED_DISCOUNT_LIFT_PER_10PP`, `OUTCOME_WINDOW_DAYS`.

## Known limits
- The supplied files are modeled/anonymized training data: results are illustrations until real exports replace them.
- Factory volumes, purchases and sales are different accounting scopes (see reconciliation); never net them against each other.
- Measured effects cover sales-side gross profit only; simultaneous changes are not separated out.
- No raw-material stock, size-level stock or real transfer costs exist in the data, so the related decisions are limited.
- Roughly 1 in 20 measured decisions can look like a lift by chance; read the claimable total as leads to verify.
