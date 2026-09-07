#!/bin/bash
# ─── Crear una instancia POS nueva (asistente) · El Choli ────────────────────
# Te pregunta los datos de la instancia y genera todo:
#   - Copia limpia del proyecto en /opt/<nombre> (sin datos)
#   - docker-compose.yml sin `name:` ni `container_name:` (evita colisiones)
#   - .env completo y listo (subdominio, CSRF, cédula del admin, secretos)
#   - (opcional) lo registra en el router y regenera su configuración
#
# Uso:
#   ./crear_pos.sh                         # asistente
#   ./crear_pos.sh pos3                    # con nombre pre-cargado
#   ./crear_pos.sh pos3 pos3.midominio.com 1234567890 8085
# Luego solo falta:  docker compose up -d --build

set -uo pipefail
cd "$(dirname "$0")/.."          # raíz de la plantilla (restaurant/)

# ─── Argumentos opcionales ────────────────────────────────────────────────────
NOMBRE="${1:-}"
SUBDOMINIO="${2:-}"
CEDULA="${3:-}"
PORT_ARG="${4:-}"

# ─── Asistente de captura de datos ────────────────────────────────────────────
validar_nombre() {
    [[ "$1" =~ ^[a-z0-9-]+$ ]] && [[ "$1" != -* ]] && [[ "$1" != *- ]]
}

read_ok() {  # falla si no hay stdin (EOF / Ctrl-D) → abortar
    if ! read -r -p "$1" "$2"; then
        echo "Abortado." >&2
        exit 1
    fi
}

while [ -z "$NOMBRE" ] || ! validar_nombre "$NOMBRE"; do
    if [ -z "$NOMBRE" ]; then
        read_ok "Nombre de la instancia (minusculas/numeros/guiones, ej: pos3): " NOMBRE
    else
        echo "  ✗ '$NOMBRE' inválido (usa minúsculas, números y guiones)."
        NOMBRE=""
    fi
done

while [ -z "$SUBDOMINIO" ] || ! [[ "$SUBDOMINIO" =~ ^[a-zA-Z0-9.-]+\.[a-z]{2,}$ ]]; do
    if [ -z "$SUBDOMINIO" ]; then
        read_ok "Subdominio final del POS (ej: $NOMBRE.midominio.com): " SUBDOMINIO
    else
        echo "  ✗ Dominio inválido (ej: pos3.midominio.com)."
        SUBDOMINIO=""
    fi
done

while [ -z "$CEDULA" ] || ! [[ "$CEDULA" =~ ^[0-9]{4,12}$ ]]; do
    if [ -z "$CEDULA" ]; then
        read_ok "Cédula del administrador inicial (solo números, ej: 1234567890): " CEDULA
    else
        echo "  ✗ Cédula inválida (solo números)."
        CEDULA=""
    fi
done

# ─── Puerto (automático si no se indica) ──────────────────────────────────────
PUERTO=""
if [ -n "$PORT_ARG" ]; then
    PUERTO="$PORT_ARG"
else
    for p in $(seq 8081 8100); do
        if ! (echo >/dev/tcp/127.0.0.1/"$p") 2>/dev/null; then
            PUERTO="$p"
            break
        fi
    done
    read_ok "Puerto del POS [$PUERTO] (Enter para aceptar): " PUERTO_ENT
    [ -n "$PUERTO_ENT" ] && PUERTO="$PUERTO_ENT"
fi
[ -z "$PUERTO" ] && { echo "ERROR: no hay puertos libres en 8081-8100." >&2; exit 1; }
if (echo >/dev/tcp/127.0.0.1/"$PUERTO") 2>/dev/null; then
    read -r -p "⚠ El puerto $PUERTO ya está en uso. ¿Continuar de todos modos? (s/N): " CONTINUAR
    [[ "$CONTINUAR" =~ ^[sSyY] ]] || { echo "Cancelado."; exit 1; }
fi

DEST="${POS_ROOT:-/opt}/${NOMBRE}"
if [ -e "$DEST" ]; then
    echo "ERROR: ya existe $DEST" >&2
    exit 1
fi

# ─── Resumen y confirmación ───────────────────────────────────────────────────
echo ""
echo "  Instancia : $NOMBRE"
echo "  Subdominio: $SUBDOMINIO"
echo "  Cédula    : $CEDULA"
echo "  Puerto    : 127.0.0.1:$PUERTO"
echo "  Carpeta   : $DEST"
if [ -t 0 ]; then
    read -r -p "¿Crear? (s/N): " CONFIRMA
    [[ "$CONFIRMA" =~ ^[sSyY] ]] || { echo "Cancelado."; exit 0; }
fi
echo ""

mkdir -p "$DEST"

echo "==> [$NOMBRE] Copiando la plantilla a $DEST ..."
tar cf - \
    --exclude=./db.sqlite3 \
    --exclude=./venv \
    --exclude=./media \
    --exclude=./staticfiles \
    --exclude=./backups \
    --exclude=./.data-migracion \
    --exclude=./.env \
    . | (cd "$DEST" && tar xf -)

echo "==> [$NOMBRE] Ajustando docker-compose.yml (quitar name/container_name) ..."
sed -i \
    -e '/^name: el-choli-pos$/d' \
    -e '/^[[:space:]]*container_name:/d' \
    "$DEST/docker-compose.yml"

echo "==> [$NOMBRE] Generando .env ..."
DJ_SECRET=$(openssl rand -hex 24)
DB_PASS=$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 24)
SU_PASS=$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 16)

sed -e "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=$DJ_SECRET|" \
    -e "s|^DJANGO_ALLOWED_HOSTS=.*|DJANGO_ALLOWED_HOSTS=$SUBDOMINIO|" \
    -e "s|^DJANGO_CSRF_TRUSTED_ORIGINS=.*|DJANGO_CSRF_TRUSTED_ORIGINS=https://$SUBDOMINIO|" \
    -e "s|^POSTGRES_DB=.*|POSTGRES_DB=el_choli_$NOMBRE|" \
    -e "s|^POSTGRES_USER=.*|POSTGRES_USER=el_choli_$NOMBRE|" \
    -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$DB_PASS|" \
    -e "s|^DJANGO_SUPERUSER_CEDULA=.*|DJANGO_SUPERUSER_CEDULA=$CEDULA|" \
    -e "s|^DJANGO_SUPERUSER_PASSWORD=.*|DJANGO_SUPERUSER_PASSWORD=$SU_PASS|" \
    -e "s|^HTTP_PORT=.*|HTTP_PORT=127.0.0.1:$PUERTO|" \
    "$DEST/.env.example" > "$DEST/.env"
chmod 600 "$DEST/.env"

mkdir -p "$DEST/media" "$DEST/staticfiles" "$DEST/backups"
chmod +x "$DEST"/scripts/*.sh "$DEST"/docker/*.sh 2>/dev/null || true

if [ "$(id -u)" = "0" ]; then
    chown -R 1000:1000 "$DEST/media" "$DEST/staticfiles"
else
    echo "AVISO: no eres root. En servidores Linux ejecuta después:"
    echo "  sudo chown -R 1000:1000 $DEST/media $DEST/staticfiles"
fi

# ─── (Opcional) registro en el router ─────────────────────────────────────────
ROUTER_DIR="${ROUTER_DIR:-/opt/router}"
if [ -f "$ROUTER_DIR/.env.router" ] && [ -t 0 ]; then
    read -r -p "¿Registrar '$SUBDOMINIO=$PUERTO' en el router y regenerar? (s/N): " REG
    if [[ "$REG" =~ ^[sSyY] ]]; then
        if grep -q "^$SUBDOMINIO=$PUERTO$" "$ROUTER_DIR/.env.router"; then
            echo "  Ya estaba registrado."
        else
            echo "$SUBDOMINIO=$PUERTO" >> "$ROUTER_DIR/.env.router"
            echo "  Añadido al router."
        fi
        (cd "$ROUTER_DIR" && bash generar_conf.sh) || \
            echo "AVISO: no se pudo regenerar el router (revisa $ROUTER_DIR)."
    fi
fi

cat <<EOF

✔ Instancia '$NOMBRE' lista en $DEST

  Subdominio: $SUBDOMINIO  →  127.0.0.1:$PUERTO
  Cédula admin: $CEDULA  |  contraseña (solo para /admin/): $SU_PASS
  DB: el_choli_$NOMBRE

Solo falta arrancarla:
  cd $DEST
  docker compose up -d --build

La instancia arranca VACÍA; en el primer arranque se crea el usuario inicial
($CEDULA) automáticamente. Loguea al POS escribiendo la cédula.
EOF