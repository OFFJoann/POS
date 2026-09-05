#!/bin/bash
# ─── Backup manual inmediato de PostgreSQL · El Choli POS ──────────────────
# Uso (en la carpeta del proyecto):
#   ./scripts/backup_db.sh
# Genera un respaldo en ./backups y limpia los antiguos según la retención.

set -euo pipefail
cd "$(dirname "$0")/.."

# Carga las variables del .env sin exponer secretos en el historial
set -a
# shellcheck disable=SC1091
source .env
set +a

mkdir -p "${BACKUP_DIR:-./backups}"

ts=$(date +%Y%m%d_%H%M%S)
file="${BACKUP_DIR:-./backups}/elcholi_${POSTGRES_DB}_${ts}.dump"

echo "==> Generando $file ..."
docker compose exec -T db pg_dump \
    -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -Z 9 > "$file"
echo "==> OK: $file ($(du -h "$file" | cut -f1))"

echo "==> Limpieza (retención ${BACKUP_RETENTION_DAYS:-30} días) ..."
find "${BACKUP_DIR:-./backups}" -name 'elcholi_*.dump' -mtime +"${BACKUP_RETENTION_DAYS:-30}" -delete -print

echo "==> Backups disponibles:"
ls -lh "${BACKUP_DIR:-./backups}"