/** Configuración: secreto compartido, huella y datos del servidor. */
import { useConfiguracion } from '../hooks/useConfiguracion'
import Cargando from '../components/Cargando'
import Secreto from '../components/Secreto'

export default function PaginaConfiguracion() {
  const { configuracion, recargar } = useConfiguracion()

  if (!configuracion) return <Cargando />

  return (
    <>
      <div className="encabezado">
        <div>
          <h1>Configuración</h1>
          <p>Datos del servidor y secreto compartido con los POS.</p>
        </div>
        <button type="button" className="boton" onClick={recargar}>Actualizar</button>
      </div>

      <div className="tarjeta">
        <div className="tarjeta__titulo">Secreto de firma (LICENCIA_SECRETO)</div>
        <div className="tarjeta__cuerpo">
          <Secreto valor={configuracion.secreto} />

          <p style={{ fontSize: 14, marginTop: 16 }}>
            Este valor debe ser <strong>idéntico</strong> en el <code>.env</code> de cada
            POS (<code>/opt/elcholi/.env</code>, <code>/opt/latimotea/.env</code>). Si
            no coincide, el POS rechaza la licencia por firma inválida.
          </p>
        </div>
      </div>

      <div className="tarjeta">
        <div className="tarjeta__titulo">Verificación rápida</div>
        <div className="tarjeta__cuerpo">
          <p style={{ fontSize: 14, marginTop: 0 }}>
            Compara esta huella con la que muestra el panel de cada POS
            (Administración → Estado de licencia). Si son iguales, los secretos
            coinciden sin exponerlos.
          </p>
          <div className="secreto">
            <code>{configuracion.huella || '—'}</code>
            <span className="insignia insignia--neutro">
              SHA-256 (12 caracteres)
            </span>
          </div>
        </div>
      </div>

      <div className="tarjeta">
        <div className="tarjeta__titulo">Servidor</div>
        <div className="tarjeta__cuerpo">
          <table className="tabla">
            <tbody>
              <tr>
                <td style={{ width: 220 }}>Licencias registradas</td>
                <td>{configuracion.total_licencias}</td>
              </tr>
              <tr>
                <td>Licencias activas</td>
                <td>{configuracion.licencias_activas}</td>
              </tr>
              <tr>
                <td>Secreto configurado</td>
                <td>
                  {configuracion.configurado ? (
                    <span className="insignia insignia--exito">Sí</span>
                  ) : (
                    <span className="insignia insignia--peligro">No</span>
                  )}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}