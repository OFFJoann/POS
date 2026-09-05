#!/bin/bash
# ─── Migración de db.sqlite3 → PostgreSQL · El Choli POS ───────────────────
# Ejecuta TODO el proceso de migración de forma segura:
#   1) Verifica que aún se usa SQLite (sin DB_HOST en el entorno).
#   2) Copia de seguridad de db.sqlite3 en backups/sqlite/ (con verificación).
#   3) Exporta los datos a .data-migracion/datos_<fecha>.json
#      (excluye tablas de infraestructura: contenttypes, permisos, sesiones, admin_log).
#   4) Carga los datos en PostgreSQL dentro de los contenedores.
#   5) Reajusta las secuencias (auto-increment) a los IDs importados.
#   6) Valida conteos de las tablas principales.
#   7) Genera el backup inicial de producción.
#
# Requisitos: Docker Compose arriba, db.sqlite3 presente y app aún en SQLite.

set -euo pipefail
cd "$(dirname "$0")/.."

set -a
# shellcheck disable=SC1091
source .env
set +a

STAMP=$(date +%Y%m%d_%H%M%S)
DATA_DIR=".data-migracion"
mkdir -p "$DATA_DIR"

# 0) Comprobación previa: la app local debe apuntar a SQLite
if [ -n "${DB_HOST:-}" ]; then
    echo "ERROR: con DB_HOST definido no se usa SQLite." >&2
    exit 1
fi

echo "========== [1/7] Backup de seguridad de db.sqlite3 =========="
mkdir -p backups/sqlite
cp db.sqlite3 "backups/sqlite/db_before_migracion_${STAMP}.sqlite3"
python -c "
import sqlite3, sys
con = sqlite3.connect(r'backups/sqlite/db_before_migracion_${STAMP}.sqlite3')
ok = con.execute('PRAGMA integrity_check;').fetchone()[0]
con.close()
print('Integridad:', ok)
sys.exit(0 if ok == 'ok' else 1)
"
echo "OK → backups/sqlite/db_before_migracion_${STAMP}.sqlite3"

echo "========== [2/7] Exportación de datos a JSON =========="
OUT="$DATA_DIR/datos_${STAMP}.json"
python manage.py dumpdata \
    --exclude contenttypes.contenttype \
    --exclude auth.permission \
    --exclude sessions.session \
    --exclude admin.logentry \
    --output "$OUT" --verbosity 1
echo "OK → $OUT"

echo "========== [3/7] Verificación del export =========="
python -c "
import json
data = json.load(open(r'$OUT'))
print(f'{len(data)} registros exportados.')
labels = sorted({d[\"model\"] for d in data})
print('Modelos:', ', '.join(labels))
"

echo "========== [4/7] Carga en PostgreSQL (contenedor app) =========="
# El entrypoint crea un superusuario automático (pk=1) en la BD nueva;
# se elimina antes de cargar para que no haya conflicto de IDs con los
# usaurios reales que vienen de SQLite (loaddata respeta los IDs originales).
docker compose run --rm app python manage.py shell -c \
    "from django.contrib.auth.models import User; print('usuarios_en_pg_a_limpiar:', User.objects.count()); User.objects.all().delete()"
docker compose run --rm \
    -v "$PWD/$DATA_DIR:/data" \
    app python manage.py loaddata "/data/$(basename "$OUT")"

echo "========== [5/7] Reajuste de secuencias PostgreSQL =========="
cat > "${BACKUP_DIR:-./backups}/reset_sequences.sql" <<'SQL'
DO $$
DECLARE r RECORD;
BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format(
      'SELECT setval(pg_get_serial_sequence(''"%s"'', ''id''), COALESCE(MAX(id), 1)) FROM "%s"',
      r.tablename, r.tablename
    );
  END LOOP;
END $$;
SQL
docker compose exec -T db psql \
    -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    -f "/backups/reset_sequences.sql"
rm -f "${BACKUP_DIR:-./backups}/reset_sequences.sql"
echo "Secuencias reajustadas."

echo "========== [6/7] Validación =========="
docker compose run --rm app python manage.py shell -c "
from django.apps import apps
for label in ['usuarios', 'productos', 'inventario', 'mesas', 'ventas', 'caja']:
    for m in apps.get_app_config(label).get_models():
        print(f'{m._meta.label_lower}: {m.objects.count()}')
from django.contrib.auth import get_user_model
print('auth.user:', get_user_model().objects.count())
"

echo "========== [7/7] Backup inicial de producción =========="
./scripts/backup_db.sh

echo ""
echo "✔ Migración completada. Los datos ya están en PostgreSQL."
echo "  - La app ahora opera con PostgreSQL."
echo "  - Respaldo SQLite en backups/sqlite/."
echo "  - Export en $DATA_DIR/."
echo "  - Backup Postgres inicial en backups/."
echo "Revisa el sistema (login, ventas, caja, reportes) y luego puedes"
echo "renombrar/archivar db.sqlite3 si todo está correcto."