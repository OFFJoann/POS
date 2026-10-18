#!/bin/sh
# ─── Recordatorios de cuotas de crédito ──────────────────────────────────────
# Corre una vez al día el comando `enviar_recordatorios_cuotas`, que avisa al
# cliente un día antes del vencimiento y el día del vencimiento. Cada cuota se
# avisa una sola vez por tipo (queda marcada en la base), así que repetir la
# ejecución no genera duplicados.
#
# Por defecto se envía a las 08:00 hora de Ecuador (UTC-5) = 13:00 UTC.
# Ajustable con la variable TARGET_HOUR_UTC en docker-compose.yml.
TARGET_HOUR_UTC="${TARGET_HOUR_UTC:-13}"

while true; do
  hour="$(date -u +%H)"
  if [ "$hour" -eq "$TARGET_HOUR_UTC" ]; then
    echo "[recordatorios] $(date -u '+%Y-%m-%d %H:%M UTC') enviando recordatorios..."
    if ! python manage.py enviar_recordatorios_cuotas; then
      echo "[recordatorios] el envío terminó con errores; se reintentará mañana"
    fi
    sleep 3600
  else
    sleep 60
  fi
done
