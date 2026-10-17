/**
 * Rutas del panel.
 *
 * Para agregar un módulo nuevo: crea `src/pages/MiModulo.jsx` y añade una
 * entrada aquí y un enlace en `src/components/Layout.jsx`.
 */
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { ProveedorSesion } from './context/ProveedorSesion'
import { useSesion } from './hooks/useSesion'
import { ProveedorConfiguracion } from './context/ProveedorConfiguracion'
import Layout from './components/Layout'
import Login from './pages/Login'
import Resumen from './pages/Resumen'
import Licencias from './pages/Licencias'
import Configuracion from './pages/Configuracion'

function Rutas() {
  const { usuario, cargando } = useSesion()

  if (cargando) {
    return (
      <div className="cargador">
        <span className="girador" />
        Cargando…
      </div>
    )
  }

  if (!usuario) {
    return (
      <Routes>
        <Route path="*" element={<Login />} />
      </Routes>
    )
  }

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Resumen />} />
        <Route path="licencias" element={<Licencias />} />
        <Route path="configuracion" element={<Configuracion />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter basename="/panel">
      <ProveedorSesion>
        <ProveedorConfiguracion>
          <Rutas />
        </ProveedorConfiguracion>
      </ProveedorSesion>
    </BrowserRouter>
  )
}