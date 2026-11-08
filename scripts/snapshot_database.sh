#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p snapshots
snapshot_tmp=$(mktemp snapshots/.kidsic-snapshot.XXXXXX)
trap 'rm -f "$snapshot_tmp"' EXIT
docker compose exec -T database pg_dump \
    --username=kidsic --dbname=kidsic --no-owner --no-acl --no-tablespaces \
    | gzip -n > "$snapshot_tmp"
gzip -t "$snapshot_tmp"
chmod 644 "$snapshot_tmp"
mv "$snapshot_tmp" snapshots/10-kidsic.sql.gz
echo "Database snapshot saved: snapshots/10-kidsic.sql.gz"
