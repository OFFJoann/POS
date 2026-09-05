#!/bin/sh
# ─── Backups automáticos de PostgreSQL · El Choli POS ───────────────────────
# Genera un backup (formato custom, comprimido) cada BACKUP_INTERVAL_HOURS.
# Conserva los backups BACKUP_RETENTION_DAYS días.
# Los backups se guardan en /backups (montado desde BACKUP_DIR del host),
# por lo que sobreviven a la eliminación de cualquier contenedor.

set -e

: "${POSTGRES_HOST:=db}"
: "${POSTGRES_PORT:=5432}"
: "${BACKUP_INTERVAL_HOURS:=24}"
: "${BACKUP_RETENTION_DAYS:=30}"

INTERVAL_SECONDS=$((BACKUP_INTERVAL_HOURS * 3600))

echo "==> [backup] Esperando base de datos $POSTGRES_HOST:$POSTGRES_PORT ..."
until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB"; do
    sleep 3
done

mkdir -p /backups

crear_backup() {
    local ts
    ts=$(date +%Y%m%d_%H%M%S)
    local file="/backups/elcholi_${POSTGRES_DB}_${ts}.dump"
    local tmp="${file}.tmp"

    echo "==> [backup] Generando $file ..."
    if pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" \
            -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
            -Fc -Z 9 -f "$tmp"; then
        mv "$tmp" "$file"
        echo "==> [backup] OK: $file ($(du -h "$file" | cut -f1))"
    else
        rm -f "$tmp"
        echo "==> [backup] ERROR al generar $file" >&2
    fi

    # Limpieza de backups antiguos y de archivos incompletos
    find /backups -name 'elcholi_*.dump' -mtime +"$BACKUP_RETENTION_DAYS" -delete
    find /backups -name 'elcholi_*.dump' -size 0 -delete
}

# Backup inmediato al arrancar
crear_backup

# Luego, en intervalos programados
while true; do
    sleep "$INTERVAL_SECONDS"
    crear_backup
done