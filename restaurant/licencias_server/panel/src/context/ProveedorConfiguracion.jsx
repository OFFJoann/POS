/** Proveedor con la configuración del servidor, cargada una sola vez. */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { obtenerConfiguracion } from '../api/licencias'
import { useSesion } from '../hooks/useSesion'
import { ConfiguracionContext } from './configuracionContext'

export function ProveedorConfiguracion({ children }) {
  const { usuario } = useSesion()
  const [guardada, setGuardada] = useState(null)

  const recargar = useCallback(() => {
    obtenerConfiguracion().then(setGuardada).catch(() => {})
  }, [])

  // La configuración es privada: solo se pide con sesión activa. Al cerrar
  // sesión deja de exponerse (sin tocar el estado y provocar un render extra).
  useEffect(() => {
    if (usuario) recargar()
  }, [usuario, recargar])

  const valor = useMemo(
    () => ({ configuracion: usuario ? guardada : null, recargar }),
    [usuario, guardada, recargar],
  )

  return (
    <ConfiguracionContext.Provider value={valor}>
      {children}
    </ConfiguracionContext.Provider>
  )
}