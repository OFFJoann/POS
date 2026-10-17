/** Acceso a la configuración del servidor. */
import { useContext } from 'react'
import { ConfiguracionContext } from '../context/configuracionContext'

export function useConfiguracion() {
  const ctx = useContext(ConfiguracionContext)
  if (!ctx) {
    throw new Error('useConfiguracion debe usarse dentro de ProveedorConfiguracion')
  }
  return ctx
}