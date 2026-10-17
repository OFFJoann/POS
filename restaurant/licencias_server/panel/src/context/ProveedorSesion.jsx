/** Proveedor de sesión: usuario actual, entrar y cerrar sesión. */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { entrar, obtenerSesion, salir } from '../api/licencias'
import { alCaducarSesion } from '../api/client'
import { SesionContext } from './sesionContext'

export function ProveedorSesion({ children }) {
  const [usuario, setUsuario] = useState(null)
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    let vivo = true
    obtenerSesion()
      .then((d) => vivo && setUsuario(d))
      .catch(() => vivo && setUsuario(null))
      .finally(() => vivo && setCargando(false))
    return () => { vivo = false }
  }, [])

  useEffect(() => {
    alCaducarSesion(() => setUsuario(null))
  }, [])

  const login = useCallback(async (username, password) => {
    await entrar(username, password)
    // Se relee la sesión en vez de fiarse de la respuesta del login: así el
    // panel usa siempre los mismos datos que el servidor, sin duplicar aquí la
    // regla de qué puede hacer cada rol.
    const d = await obtenerSesion()
    setUsuario(d)
    return d
  }, [])

  const logout = useCallback(async () => {
    try {
      await salir()
    } finally {
      setUsuario(null)
    }
  }, [])

  // `puedeEscribir` es la pregunta que se hacen todas las pantallas para
  // decidir si muestran botones de escritura. Viene del servidor.
  const valor = useMemo(
    () => ({
      usuario,
      cargando,
      login,
      logout,
      puedeEscribir: usuario?.puede_escribir === true,
    }),
    [usuario, cargando, login, logout],
  )

  return <SesionContext.Provider value={valor}>{children}</SesionContext.Provider>
}