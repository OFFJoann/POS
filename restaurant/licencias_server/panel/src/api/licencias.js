/** Endpoints del panel de licencias. */
import { api, refrescarCsrf } from './client'

export const obtenerSesion = () => api('/api/panel/sesion/')

export async function entrar(username, password) {
  const datos = await api('/api/panel/login/', {
    method: 'POST',
    body: { username, password },
  })
  // El login rota el secreto CSRF: hay que pedir uno nuevo.
  await refrescarCsrf()
  return datos
}

export async function salir() {
  const datos = await api('/api/panel/logout/', { method: 'POST' })
  await refrescarCsrf()
  return datos
}

export const obtenerResumen = () => api('/api/panel/dashboard/')

export const obtenerConfiguracion = () => api('/api/panel/configuracion/')

export const listarLicencias = (filtros = {}) => {
  const params = new URLSearchParams()
  if (filtros.q) params.set('q', filtros.q)
  if (filtros.estado) params.set('estado', filtros.estado)
  const qs = params.toString()
  return api(`/api/panel/licencias/${qs ? `?${qs}` : ''}`)
}

export const crearLicencia = (datos) =>
  api('/api/panel/licencias/', { method: 'POST', body: datos })

export const actualizarLicencia = (id, datos) =>
  api(`/api/panel/licencias/${id}/`, { method: 'PUT', body: datos })

export const eliminarLicencia = (id) =>
  api(`/api/panel/licencias/${id}/`, { method: 'DELETE' })

export const ejecutarAcciones = (ids, accion, extra = {}) =>
  api('/api/panel/licencias/acciones/', {
    method: 'POST',
    body: { ids, accion, ...extra },
  })