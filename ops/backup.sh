#!/usr/bin/env sh
# Nightly PostgreSQL backup (run from the host via cron):  0 2 * * * /opt/merch-brain/ops/backup.sh
set -eu
mkdir -p backups
docker compose exec -T postgres pg_dump -U merch -Fc merchbrain > "backups/merchbrain-$(date +%Y%m%d-%H%M).dump"
find backups -name 'merchbrain-*.dump' -mtime +14 -delete
