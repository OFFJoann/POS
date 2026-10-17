/** Layout con menú lateral. Los módulos nuevos se añaden aquí. */
import { NavLink, Outlet } from 'react-router-dom'
import { useSesion } from '../hooks/useSesion'
import { useConfiguracion } from '../hooks/useConfiguracion'

export default function Layout() {
  const { usuario, logout } = useSesion()
  const { configuracion } = useConfiguracion()

  return (
    <div className="app">
      <nav className="lateral">
        <div className="lateral__marca">
          TorreApp
          <small>Panel de licencias</small>
        </div>

        <div className="lateral__grupo">Operación</div>
        <NavLink to="/" end className="lateral__enlace">
          Resumen
        </NavLink>
        <NavLink to="/licencias" className="lateral__enlace">
          Licencias
        </NavLink>

        {/* Aquí aparecerán los módulos nuevos */}
        <div className="lateral__grupo">Sistema</div>
        <NavLink to="/configuracion" className="lateral__enlace">
          Configuración
        </NavLink>

        <div className="lateral__pie">
          <div style={{ color: '#e2e8f0', marginBottom: 8 }}>{usuario?.username}</div>
          <button
            type="button"
            className="boton boton--pequeno"
            onClick={logout}
          >
            Cerrar sesión
          </button>
          {configuracion && (
            <div style={{ color: '#64748b', fontSize: 12, marginTop: 10 }}>
              {configuracion.total_licencias} licencia(s) ·{' '}
              {configuracion.licencias_activas} activa(s)
            </div>
          )}
        </div>
      </nav>

      <main className="principal">
        <Outlet />
      </main>
    </div>
  )
}