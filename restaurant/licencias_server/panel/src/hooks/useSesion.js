/** Acceso al contexto de sesión. */
import { useContext } from 'react'
import { SesionContext } from '../context/sesionContext'

export function useSesion() {
  const ctx = useContext(SesionContext)
  if (!ctx) throw new Error('useSesion debe usarse dentro de ProveedorSesion')
  return ctx
}