#!/bin/bash
# ─── Genera el nginx.conf del router multi-POS · El Choli ────────────────────
# Lee .env.router (uno por servidor) y produce router/nginx.conf con un bloque
# server por subdominio. Luego recarga/levanta el contenedor del router.
#
# Uso:
#   cp .env.router.example .env.router   # edita subdominios → puertos
#   ./generar_conf.sh

set -euo pipefail
cd "$(dirname "$0")"

ENV_FILE=".env.router"
OUT="nginx.conf"

if [ ! -f "$ENV_FILE" ]; then
    echo "No existe $ENV_FILE. Copia la plantilla: cp .env.router.example $ENV_FILE"
    exit 1
fi

# Configuración del router (líneas CLAVE=valor)
ROUTER_SSL=false
ROUTER_HTTP_PORT=80
ROUTER_HTTPS_PORT=443
while IFS='=' read -r clave valor; do
    case "$clave" in
        ROUTER_SSL)       ROUTER_SSL="$valor" ;;
        ROUTER_HTTP_PORT) ROUTER_HTTP_PORT="$valor" ;;
        ROUTER_HTTPS_PORT) ROUTER_HTTPS_PORT="$valor" ;;
    esac
done < <(grep -E '^ROUTER_[A-Z_]+=' "$ENV_FILE" || true)

SSL_BOOL=$(echo "$ROUTER_SSL" | tr '[:upper:]' '[:lower:]')
SSL_ON=false
case "$SSL_BOOL" in
    true|1|yes|on) SSL_ON=true ;;
esac

: > "$OUT"
FOUND=0

# Bloques de servidor por subdominio
while IFS='=' read -r sub puerto; do
    sub_trim=$(echo "$sub" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
    [ -z "$sub_trim" ] && continue
    case "$sub_trim" in \#*) continue ;; ROUTER_*) continue ;; esac
    if ! echo "$puerto" | grep -qE '^[0-9]+$'; then
        echo "Advertencia: línea inválida (se omite): $sub_trim=$puerto" >&2
        continue
    fi
    FOUND=$((FOUND + 1))

    if [ "$SSL_ON" = true ]; then
        {
            echo "server {"
            echo "    listen $ROUTER_HTTPS_PORT ssl;"
            echo "    server_name $sub_trim;"
            echo ""
            echo "    ssl_certificate     /etc/nginx/certs/fullchain.pem;"
            echo "    ssl_certificate_key /etc/nginx/certs/privkey.pem;"
            echo "    ssl_protocols TLSv1.2 TLSv1.3;"
            echo ""
            echo "    location / {"
            echo "        proxy_pass http://127.0.0.1:$puerto;"
            echo "        proxy_set_header Host \$host;"
            echo "        proxy_set_header X-Real-IP \$remote_addr;"
            echo "        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;"
            echo "        proxy_set_header X-Forwarded-Proto https;"
            echo "    }"
            echo "}"
            echo ""
            echo "server {"
            echo "    listen $ROUTER_HTTP_PORT;"
            echo "    server_name $sub_trim;"
            echo "    return 301 https://\$host\$request_uri;"
            echo "}"
            echo ""
        } >> "$OUT"
    else
        {
            echo "server {"
            echo "    listen $ROUTER_HTTP_PORT;"
            echo "    server_name $sub_trim;"
            echo ""
            echo "    location / {"
            echo "        proxy_pass http://127.0.0.1:$puerto;"
            echo "        proxy_set_header Host \$host;"
            echo "        proxy_set_header X-Real-IP \$remote_addr;"
            echo "        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;"
            echo "        proxy_set_header X-Forwarded-Proto http;"
            echo "    }"
            echo "}"
            echo ""
        } >> "$OUT"
    fi
done < <(grep -E '^[A-Za-z0-9_.-]+=[0-9]+$' "$ENV_FILE" || true)

if [ "$FOUND" -eq 0 ]; then
    echo "No hay instancias configuradas en $ENV_FILE (líneas: subdominio=puerto)." >&2
    exit 1
fi

# Servidor por defecto: descarta hosts no listados (HTTP y/o HTTPS)
if [ "$SSL_ON" = true ]; then
    {
        echo "server {"
        echo "    listen $ROUTER_HTTP_PORT default_server;"
        echo "    listen $ROUTER_HTTPS_PORT ssl default_server;"
        echo "    ssl_certificate     /etc/nginx/certs/fullchain.pem;"
        echo "    ssl_certificate_key /etc/nginx/certs/privkey.pem;"
        echo "    server_name _;"
        echo "    return 444;"
        echo "}"
    } >> "$OUT"
else
    {
        echo "server {"
        echo "    listen $ROUTER_HTTP_PORT default_server;"
        echo "    server_name _;"
        echo "    return 444;"
        echo "}"
    } >> "$OUT"
fi

echo "✔ Generado $OUT con $FOUND instancia(s)."

if command -v docker >/dev/null 2>&1 && docker ps >/dev/null 2>&1; then
    docker compose up -d 2>/dev/null || true
    docker compose exec -T router nginx -s reload >/dev/null 2>&1 \
        && echo "✔ Router recargado." \
        || echo "✔ Configuración lista (levanta el router con: docker compose up -d)"
fi