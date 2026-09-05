#!/bin/bash
# ─── Restauración de PostgreSQL · El Choli POS ─────────────────────────────
# Uso:
#   ./scripts/restore_db.sh                # lista backups y pide elegir uno
#   ./scripts/restore_db.sh backups/archivo.dump   # restaura ese archivo
#
# ADVERTENCIA: reemplaza TODOS los datos de la base de datos actual.

set -euo pipefail
cd "$(dirname "$0")/.."

set -a
# shellcheck disable=SC1091
source .env
set +a

backup_dir="${BACKUP_DIR:-./backups}"

if [ $# -ge 1 ]; then
    file="$1"
else
    echo "==> Backups disponibles en $backup_dir:"
    ls -1t "$backup_dir"/elcholi_*.dump 2>/dev/null || { echo "No hay backups."; exit 1; }
    read -r -p "==> Nombre del backup a restaurar: " file
fi

if [ ! -f "$file" ]; then
    echo "ERROR: no existe '$file'" >&2
    exit 1
fi

echo "==> Restaurando '$file' en la base ${POSTGRES_DB} ..."
read -r -p "==> ¿Continuar? Se perderán los datos actuales del contenedor. (s/N) " resp
case "$resp" in
    [sSyY]*) ;;
    *) echo "Cancelado."; exit 1 ;;
esac

container_file="/backups/$(basename "$file")"

docker compose exec -T db pg_restore \
    --clean --if-exists --no-owner --no-privileges \
    -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$container_file"

echo "==> Restauración completada."