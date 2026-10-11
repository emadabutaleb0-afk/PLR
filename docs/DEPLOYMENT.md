# Deployment, operations, backups
## First install
1. `cp .env.example .env` and set strong `POSTGRES_PASSWORD`, `SECRET_KEY` (≥ 32 random chars), `BOOTSTRAP_ADMIN_PASSWORD`, `CORS_ORIGINS` (your internal URL).
2. Put the 20 CSVs in `data/private/` (or set `COMPANY_DATA_PATH`). Never commit them.
3. `docker compose up --build -d`. The backend runs `alembic upgrade head` at start.
4. Open http://server:3000 → sign in → Data Health → **Refresh data**. Create users with `POST /api/v1/auth/users` (CEO only); STORE_MANAGER needs `allowed_locations`.
5. Put the stack behind your company reverse proxy with TLS (HSTS is already sent). Do not expose Postgres/Redis ports.

## Daily refresh
Overwrite the CSVs in the data folder and press **Refresh data** (or `POST /api/v1/data/import`). Bad rows are quarantined, never loaded; failed files keep their previous data; decisions/feedback survive refreshes (stable recommendation keys).

## Backups
`ops/backup.sh` (cron) writes a custom-format dump to `./backups` and keeps 14 days. Restore: `docker compose exec -T postgres pg_restore -U merch -d merchbrain --clean < backups/<file>.dump`. Also back up the `models` volume (or simply retrain: `POST /api/v1/jobs/retrain`). Business tables can always be rebuilt from the CSVs; **users, audit logs, feedback and actions exist only in the database** — those are what the backup protects.

## Monitoring
`docker compose --profile monitoring up -d` → Prometheus :9090, Grafana :3001. Metrics: request count/latency/errors, job duration, import failures, model age, data age. `/health` for liveness.

## Hardening checklist
change bootstrap password · rotate SECRET_KEY on compromise (invalidates sessions) · restrict network access to the proxy · run behind TLS · keep rate limit enabled (limiter is per process; use the proxy for global limits) · review audit logs.
