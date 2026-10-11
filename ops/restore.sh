#!/usr/bin/env sh
# Restore a PostgreSQL backup made by ops/backup.sh.   Usage: ops/restore.sh backups/merchbrain-YYYYMMDD-HHMM.dump
# This REPLACES the current database. A safety dump of the current state is taken first.
set -eu
[ $# -eq 1 ] && [ -f "$1" ] || { echo "usage: $0 <backup.dump>"; exit 2; }
mkdir -p backups
docker compose exec -T postgres pg_dump -U merch -Fc merchbrain > "backups/before-restore-$(date +%Y%m%d-%H%M).dump"
docker compose stop backend worker frontend
docker compose exec -T postgres psql -U merch -d postgres -c "DROP DATABASE IF EXISTS merchbrain WITH (FORCE);" -c "CREATE DATABASE merchbrain OWNER merch;"
docker compose exec -T postgres pg_restore -U merch -d merchbrain --no-owner < "$1"
docker compose start backend worker frontend
echo "Restored from $1. Open Data Health and check the latest refresh date."
