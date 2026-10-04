#!/usr/bin/env bash
# Stop the Apple-`container` stack. Volumes are kept unless --wipe is passed.
# Equivalent of `docker compose down` / `docker compose down -v`.
set -euo pipefail
command -v container >/dev/null 2>&1 || { echo "[container] not installed"; exit 0; }

for c in day19-qdrant day19-redis day19-postgres; do
  container stop "$c" >/dev/null 2>&1 && echo "[container] stopped $c" || true
  container rm   "$c" >/dev/null 2>&1 || true
done

if [ "${1:-}" = "--wipe" ]; then
  for v in day19-qdrant-storage day19-redis-data day19-postgres-data; do
    container volume delete "$v" >/dev/null 2>&1 && echo "[container] wiped volume $v" || true
  done
fi
echo "[container] done"
