# El Choli POS · Producción con Docker Compose

Infraestructura de producción completamente dockerizada. La aplicación corre en
Django/Gunicorn detrás de nginx, con PostgreSQL 16 como base de datos y backups
automáticos.

## Arquitectura

| Servicio   | Imagen              | Función                                          |
|------------|---------------------|--------------------------------------------------|
| `db`       | postgres:16-alpine  | Base de datos PostgreSQL (persistente en volumen)|
| `backup`   | postgres:16-alpine  | Backups automáticos programados                  |
| `app`      | Python 3.13 slim    | Django + Gunicorn (migraciones, estáticos)       |
| `nginx`    | nginx:1.27-alpine   | Estáticos, media y proxy inverso                 |

- **Reinicio automático**: todos los contenedores usan `restart: unless-stopped`.
- **Persistencia**: datos DB en el volumen `pgdata`; media y estáticos en carpetas
  del host (`media/`, `staticfiles/`); backups en `backups/` (host).

## Estructura

```
restaurant/
├── docker-compose.yml      # servicio completo (usa .env)
├── .env                    # secretos/configuración (NO va a git)
├── .env.example            # plantilla de configuración
├── Dockerfile              # imagen de la aplicación
├── .dockerignore
├── docker/
│   ├── entrypoint.sh       # migraciones + estáticos + usuario inicial (cédula) + gunicorn
│   ├── nginx.conf          # configuración de nginx (incluye HTTPS opcional)
│   └── backup.sh           # script de backups automáticos
├── scripts/
│   ├── backup_db.sh        # backup manual inmediato
│   ├── restore_db.sh       # restauración desde un backup
│   ├── migrar_a_postgres.sh# migración completa desde db.sqlite3
│   └── crear_pos.sh        # crea una instancia POS nueva por subdominio
├── router/                 # nginx multi-POS (un router por servidor)
└── backups/                # backups de PostgreSQL (host)
```

## Requisitos del servidor

- Docker Engine + Docker Compose v2.
- **Inicio automático de Docker** (para que todo arranque con el servidor):
  ```bash
  sudo systemctl enable --now docker
  ```
- En Windows (Docker Desktop): activar *"Start Docker Desktop when you sign in"*.

## Configuración inicial

```bash
cp .env.example .env
# edita .env: DJANGO_SECRET_KEY, POSTGRES_PASSWORD, DJANGO_ALLOWED_HOSTS,
# DJANGO_CSRF_TRUSTED_ORIGINS, DJANGO_SUPERUSER_*
```

**Permisos en Linux** (una sola vez; solo en Linux, no en Docker Desktop):
```bash
sudo chown -R 1000:1000 staticfiles media   # UID del usuario appuser
chmod 600 .env
```

## Primer arranque y validación

```bash
docker compose up -d --build
docker compose ps          # todos deben estar "Up" y "healthy"
```

- Aplicación: `http://<servidor>/` (login con **cédula**, sin contraseña)
- Chequeo de salud: `http://<servidor>/healthz/` → `{"status": "ok"}`
- Administración: `http://<servidor>/admin/` (usuario del `.env`)
- Registro en la primera ejecución: el entrypoint ejecuta `migrate`,
  `collectstatic` y crea el **usuario inicial por cédula** automáticamente
  (User superuser + perfil Vendedor). Ese usuario es administrador (`is_staff`)
  y entra al POS escribiendo su cédula.

Variables útiles en `.env`:

| Variable                  | Ejemplo                        | Nota                          |
|---------------------------|--------------------------------|-------------------------------|
| `BACKUP_INTERVAL_HOURS`   | `24`                           | Cada cuántas horas un backup  |
| `BACKUP_RETENTION_DAYS`   | `30`                           | Días que se conservan         |
| `HTTP_PORT`               | `80`                           | Puerto HTTP en el host        |
| `GUNICORN_WORKERS`        | `3`                            | Workers de Gunicorn           |
| `DJANGO_ENABLE_SSL`       | `True` (con HTTPS)             | Cookies seguras + proxy       |

## Backups

### Automáticos
El servicio `backup` genera un respaldo al arrancar y luego cada
`BACKUP_INTERVAL_HOURS`. Se guardan como `backups/elcholi_<fecha>.dump`
(formato comprimido `pg_dump -Fc`), **fuera de los contenedores**, por lo que
sobreviven a `docker compose down -v`.

### Manual
```bash
./scripts/backup_db.sh
```

### Restauración
```bash
./scripts/restore_db.sh                       # lista y pide elegir
./scripts/restore_db.sh backups/elcholi_xxxx.dump
```
> **Advertencia:** la restauración reemplaza los datos actuales del contenedor.

Recuperación ante pérdida de datos:

```bash
docker compose up -d                          # si el contenedor DB no existe, se recrea
./scripts/restore_db.sh backups/elcholi_xxxx.dump
docker compose restart app
```

## Actualización de la aplicación (sin afectar datos)

```bash
git pull
docker compose up -d --build                  # la app se reconstruye; el volumen pgdata se conserva
```

Los datos, media y backups viven en el host/volumen, no en la imagen.

## Múltiples POS en el mismo servidor (por subdominio)

Cada POS es una copia del proyecto en su propia carpeta (`/opt/pos1`, `/opt/pos2`, ...),
cada una con su `.env` (puerto propio `127.0.0.1:808X`, subdominio, cédula admin).
Un **router nginx** reparte el tráfico según el subdominio a cada puerto.

### 1) Crear una instancia

```bash
cd /opt/elcholi/restaurant
./crear_pos.sh                    # asistente: te pide nombre, subdominio, cédula, puerto
```

El asistente crea la copia en `/opt/<nombre>` y escribe el `.env` completo
(subdominio, CSRF, cédula del admin, secretos únicos, puerto `127.0.0.1:808X`),
quita `name:`/`container_name:` del compose y, si el router existe en `/opt/router`,
lo registra automáticamente. **Solo falta arrancar**:

```bash
cd /opt/pos3
docker compose up -d --build
```

> La instancia arranca **vacía**: en el primer arranque se crea solo el usuario
> inicial (por cédula). El asistente también acepta argumentos posicionales:
> `./crear_pos.sh pos3 pos3.midominio.com 1234567890 8085`.

### 2) Router

```bash
mkdir -p /opt/router && cd /opt/router
cp /opt/elcholi/restaurant/router/{docker-compose.yml,generar_conf.sh,.env.router.example} .
cp .env.router.example .env.router       # edita: subdominio=puerto por línea
./generar_conf.sh                        # genera nginx.conf y levanta el router
```

- DNS: los registros `A` de `pos1`, `pos2`, ... apuntan todos a la IP del servidor.
- Config del router: `ROUTER_SSL=false` (HTTP) o `true` (HTTPS con certificado
  wildcard en `certs/fullchain.pem` + `certs/privkey.pem`).
- Cada subdominio se agrega como `posN.midominio.com=808N`.
- El router con `network_mode: host` escucha en los puertos 80/443 del servidor y
  reenvía a `127.0.0.1:<puerto>` de cada instancia (los POS no quedan expuestos).
- Para descartar hosts no listados se responde `444`.

### 3) HTTPS

Certificado wildcard `*.tudominio.com` (Let's Encrypt), colócalo en `certs/`,
pon `ROUTER_SSL=true` y vuelve a ejecutar `./generar_conf.sh`. Cada instancia debe
tener en su `.env`: `DJANGO_ENABLE_SSL=True` y `DJANGO_CSRF_TRUSTED_ORIGINS=https://<subdominio>`.

## Migración desde db.sqlite3 → PostgreSQL

Proceso (una sola vez, con la app **aún en SQLite** en este equipo):

1. **Copia de seguridad de SQLite** con verificación de integridad.
2. **Exportación** a JSON (excluye tablas de infraestructura).
3. **Carga** en PostgreSQL (los IDs y relaciones se conservan).
4. **Reajuste de secuencias** (auto-increment).
5. **Validación** de conteos y acceso.
6. **Backup inicial** de producción.

### Automático (si tienes bash en este equipo, git-bash/WSL):

```bash
./scripts/migrar_a_postgres.sh
```

### Manual (PowerShell, equipo Windows):

```powershell
# 1) Backup de seguridad de db.sqlite3
New-Item -ItemType Directory -Force -Path "backups\sqlite" | Out-Null
Copy-Item db.sqlite3 "backups\sqlite\db_before_migracion_$(Get-Date -Format yyyyMMdd_HHmmss).sqlite3"
venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect(r'backups\sqlite\db_before_migracion_*.sqlite3'.replace('*','').replace('','')) or 0" # (se verifica interactivamente)

# 2) Exportar datos a JSON
venv\Scripts\python.exe manage.py dumpdata `
  --exclude contenttypes.contenttype --exclude auth.permission `
  --exclude sessions.session --exclude admin.logentry `
  --output .data-migracion\datos.json --verbosity 1

# 3) Cargar en PostgreSQL (contenedor app)
docker compose run --rm -v "$PWD\.data-migracion:/data" app python manage.py loaddata /data/datos.json

# 4) Reajustar secuencias (escríbelo en backups\reset.sql y ejecútalo):
docker compose exec -T db psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -f /backups/reset.sql

# 5) Validación (conteos + login en el navegador + reportes)
docker compose run --rm app python manage.py shell -c "from apps.mesas.models import Pedido; from apps.ventas.models import Factura; print('pedidos',Pedido.objects.count(),'facturas',Factura.objects.count())"

# 6) Backup inicial de producción
bash scripts/backup_db.sh
```

Usuarios, pedidos, facturas, pagos, inventario, categorías (con su orden) y la
configuración se conservan con sus IDs y relaciones. El script reajusta
automáticamente los contadores `id` para que no haya conflictos al crear registros nuevos.

> El export excluye `contenstypes`, `permissions` y `sessions` porque se regeneran
> de forma automática en la base nueva.

Después de validar, archiva `db.sqlite3` (renómbralo, no lo borres).

## HTTPS (recomendado)

1. Consigue certificados (Let's Encrypt con certbot, o Cloudflare origin cert).
2. En `docker/nginx.conf`, descomenta el bloque `listen 443`.
3. Monta los certificados en el servicio `nginx` (volumen host) y deja que apunten
   a `/etc/nginx/certs/`.
4. En `.env`: `DJANGO_ENABLE_SSL=True` y añade `https://<dominio>` a
   `DJANGO_CSRF_TRUSTED_ORIGINS`.
5. `docker compose up -d` y reinicia nginx.

## Comandos útiles

```bash
docker compose ps                 # estado de servicios
docker compose logs -f app        # logs de la aplicación
docker compose logs -f backup     # logs de backups
docker compose down               # detiene (NO borra datos/backups)
docker compose down -v            # ⚠ borra volumen pgdata (¡pierdes datos!)
docker compose restart app
```