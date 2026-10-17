# Panel de licencias (dashboard)

Dashboard web del servidor central de licencias. Es una SPA de **React 19 +
Vite** que consume la API JSON de Django (`/api/panel/...`).

## Puesta en marcha

El `docker compose up -d --build` del servidor **ya compila este panel** dentro
de la imagen, así que en producción no hace falta Node:

```
http://localhost:8010/panel/
```

El Django Admin (`/admin/`) queda como respaldo.

### Desarrollo con recarga en caliente

```bash
cd panel
npm install
npm run dev        # http://localhost:5173/panel/
```

Vite hace proxy de `/api` a `http://localhost:8010`, por eso el login y los
datos funcionan igual que en producción. Requiere el servidor Docker corriendo.

## Estructura

```
src/
  api/
    client.js          Cliente HTTP: sesión + CSRF, reintento en 403
    licencias.js       Endpoints del panel
  components/
    Layout.jsx         Menú lateral (aquí van los módulos nuevos)
    Modal.jsx          Ventana modal reutilizable
    Campo.jsx          Campo de formulario con etiqueta y ayuda
    FormularioLicencia.jsx
    Secreto.jsx        Secreto oculto con botones "Mostrar" y "Copiar"
  context/
    sesionContext.js            Objeto de contexto (sin JSX)
    ProveedorSesion.jsx         Estado de autenticación
    configuracionContext.js
    ProveedorConfiguracion.jsx  Secreto/huella/contadores
  hooks/
    useSesion.js
    useConfiguracion.js
  pages/
    Login.jsx
    Resumen.jsx
    Licencias.jsx
    Configuracion.jsx
  utils/
    formato.js          Fechas en español, dinero, estados, insignias
  App.jsx               Rutas
  index.css             Estilos (variables CSS al inicio)
```

## Mensualidad e ingresos

Cada licencia tiene un precio mensual (`mensualidad`, `Decimal` con 2 decimales).
El resumen lo convierte en dinero facturado:

- **Ingreso mensual**: suma de las licencias **activas y no vencidas**. Es lo que
  entra de verdad este mes.
- **Proyección anual**: ese mismo total × 12.
- **Si se activara todo**: suma de *todas* las licencias, incluidas pausadas y
  vencidas. Sirve para ver cuánto se deja de facturar.

El listado de Licencias muestra la mensualidad de cada fila y un pie con la suma
de lo que haya en la vista actual (útil al filtrar por estado).

El símbolo de la moneda está en `src/utils/formato.js`, constante
`SIMBOLO_MONEDA` (por defecto `RD$`). La API siempre manda los importes como
texto (`"1500.00"`) para no perder decimales al serializar a JSON.

La mensualidad **no** forma parte del payload firmado: el POS sigue validando
exactamente el mismo mensaje HMAC de antes, así que añadir el campo no obliga a
renovar ni a tocar ningún `.env`.

## Actualizar mensualidad

La venta es mensual, así que las licencias nuevas nacen con **30 días** de
vigencia. Para una venta anual se pasa la fecha explícita al crear o se extiende
con `+30/+60/+90 días`.

El botón **Mensualidad** de cada fila (y el homónimo de la barra de selección)
registra que el mes ya está pagado. Hace exactamente tres cosas:

1. Suma 30 días a la fecha de vencimiento.
2. Reactiva la licencia, aunque estuviera pausada.
3. Si ya estaba vencida, el mes nuevo arranca **desde hoy**, no desde la fecha
   vieja: el cliente recibe 30 días completos aunque haya pagado con retraso.

La regla de "cuál de las dos fechas manda" es `max(fecha_vencimiento, hoy)` en
`licencias/api.py`. El botón **no manda cuántos días**; los pone el servidor
(constante `DIAS_MENSUALIDAD`), para que la etiqueta y lo que ocurre no puedan
desincronizarse. El Admin tiene la acción equivalente.

Como no hay forma de revertirlo desde el panel, estas acciones pasan por un
diálogo de confirmación que muestra a quién y hasta qué fecha quedaría cada
licencia, y los botones quedan deshabilitados mientras se aplican para que un
doble clic no cobre dos meses.

El filtro **Pendientes de cobro** (y el contador junto a los filtros) listan lo
que vence en 30 días o menos, más lo pausado y lo vencido: es la lista de trabajo
del mes. Marcar una licencia como pagada la saca de ahí, sin tocar el precio.

## Agregar un módulo nuevo

1. Crear `src/pages/MiModulo.jsx`.
2. Añadir su endpoint en `licencias_server/licencias/api.py` y registrarlo en
   `licencias_server/licencias/urls.py` (con el decorador
   `@requiere_superusuario`).
3. Añadir el enlace en el menú de `src/components/Layout.jsx`.
4. Añadir la ruta en `src/App.jsx`.

## Autenticación

Django usa sesión + CSRF, no tokens en el navegador:

- `GET /api/panel/login/` entrega el token CSRF.
- `POST /api/panel/login/` autentica y abre sesión.
- Tras iniciar o cerrar sesión **hay que refrescar el token**: Django rota el
  secreto CSRF en esos momentos. `src/api/client.js` lo hace y además reintenta
  una vez si recibe 403.

## Despliegue

- Vite emite los assets bajo `/static/panel/`; el entrypoint copia `dist/` a
  `staticfiles/panel/` y WhiteNoise los sirve.
- Cualquier ruta bajo `/panel/` devuelve `index.html` para que React Router
  resuelva el enlace en el navegador. Excepción: `/panel/api/...` devuelve `404`
  en JSON, para que un endpoint mal escrito no se trague el HTML de la SPA.
- La API del panel vive en `/api/panel/` (fuera de `/panel/`).
- En producción, sírvelo detrás de **HTTPS**: la cookie de sesión viaja en claro
  sin TLS.