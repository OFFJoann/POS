/**
 * Cliente HTTP del panel.
 *
 * Django usa sesión + CSRF, así que cada petición de escritura envía el token
 * que devuelve `GET /api/panel/login/`. Si la sesión caduca, el backend
 * responde 401 y aquí se dispara el callback de expiración.
 */

let csrfToken = null
let onSesionCaducada = () => {}

export function alCaducarSesion(fn) {
  onSesionCaducada = fn
}

/**
 * Pide un token CSRF nuevo.
 *
 * Hay que refrescarlo tras iniciar y cerrar sesión: Django rota el secreto en
 * esos momentos, así que el token guardado en memoria dejaría de coincidir
 * con la cookie y toda escritura devolvería 403.
 */
export async function refrescarCsrf() {
  const res = await fetch('/api/panel/login/', { credentials: 'same-origin' })
  const datos = await res.json()
  csrfToken = datos.csrf || null
  return csrfToken
}

export async function api(ruta, opciones = {}, reintento = true) {
  const metodo = (opciones.method || 'GET').toUpperCase()

  if (metodo !== 'GET' && !csrfToken) await refrescarCsrf()

  const cabeceras = { ...(opciones.headers || {}) }
  if (opciones.body !== undefined) cabeceras['Content-Type'] = 'application/json'
  if (csrfToken) cabeceras['X-CSRFToken'] = csrfToken

  const res = await fetch(ruta, {
    method: metodo,
    credentials: 'same-origin',
    headers: cabeceras,
    body: opciones.body !== undefined ? JSON.stringify(opciones.body) : undefined,
  })

  let datos = {}
  try {
    datos = await res.json()
  } catch {
    datos = {}
  }

  // Un 403 casi siempre es un token CSRF caducado: se refresca y se reintenta.
  if (res.status === 403 && reintento) {
    await refrescarCsrf()
    return api(ruta, opciones, false)
  }

  if (res.status === 401) {
    onSesionCaducada()
    throw new Error(datos.error || 'Sesión expirada')
  }
  if (!res.ok || datos.ok === false) {
    throw new Error(datos.error || `Error ${res.status}`)
  }
  return datos
}