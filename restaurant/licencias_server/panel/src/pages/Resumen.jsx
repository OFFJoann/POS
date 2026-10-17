/** Portada: métricas y próximos vencimientos. */
import { useEffect, useState } from 'react'
import Cargando from '../components/Cargando'
import { Link } from 'react-router-dom'
import { obtenerResumen, listarLicencias } from '../api/licencias'
import { fecha, estadoLicencia, dinero } from '../utils/formato'

export default function PaginaResumen() {
  const [resumen, setResumen] = useState(null)
  const [proximas, setProximas] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    obtenerResumen().then(setResumen).catch((e) => setError(e.message))
    listarLicencias({ estado: 'por_vencer' })
      .then((d) => setProximas(d.licencias.slice(0, 5)))
      .catch(() => {})
  }, [])

  if (error) {
    return <div className="aviso aviso--error">No se pudo cargar el resumen: {error}</div>
  }
  if (!resumen) return <Cargando />

  const metricas = [
    { etiqueta: 'Licencias', valor: resumen.total },
    { etiqueta: 'Activas', valor: resumen.activas, clase: 'metrica--exito' },
    { etiqueta: 'Pausadas', valor: resumen.pausadas, clase: '' },
    { etiqueta: 'Vencidas', valor: resumen.vencidas, clase: 'metrica--peligro' },
    { etiqueta: 'Vencen en 30 días', valor: resumen.por_vencer_30, clase: 'metrica--alerta' },
    { etiqueta: 'Suma de límites', valor: resumen.limite_vendedores_total, clase: '' },
  ]

  return (
    <>
      <div className="encabezado">
        <div>
          <h1>Resumen</h1>
          <p>Estado de las licencias emitidas a los POS.</p>
        </div>
        <Link to="/licencias" className="boton boton--primario">Ver todas</Link>
      </div>

      <div className="tarjeta tarjeta--ingreso">
        <div className="ingreso__principal">
          <div className="ingreso__etiqueta">Ingreso mensual</div>
          <div className="ingreso__valor">{dinero(resumen.ingreso_mensual)}</div>
          <div className="ingreso__nota">
            Suma de las licencias activas y no vencidas.
          </div>
        </div>
        <div className="ingreso__laterales">
          <div>
            <div className="ingreso__etiqueta">Proyección anual</div>
            <div className="ingreso__valor ingreso__valor--chico">
              {dinero(resumen.ingreso_anual)}
            </div>
            <div className="ingreso__nota">12 meses al mismo ritmo.</div>
          </div>
          <div>
            <div className="ingreso__etiqueta">Si se activara todo</div>
            <div className="ingreso__valor ingreso__valor--chico">
              {dinero(resumen.ingreso_potencial)}
            </div>
            <div className="ingreso__nota">Incluye pausadas y vencidas.</div>
          </div>
        </div>
      </div>

      <div className="rejilla rejilla--3">
        {metricas.map((m) => (
          <div key={m.etiqueta} className={`tarjeta metrica ${m.clase}`}>
            <div className="metrica__valor">{m.valor}</div>
            <div className="metrica__etiqueta">{m.etiqueta}</div>
          </div>
        ))}
      </div>

      <div className="tarjeta">
        <div className="tarjeta__titulo">Próximos vencimientos</div>
        {proximas.length === 0 ? (
          <div className="vacio">Ninguna licencia vence en los próximos 30 días.</div>
        ) : (
          <div className="tabla-envoltura">
            <table className="tabla">
              <thead>
                <tr>
                  <th>Código</th>
                  <th>Cliente</th>
                  <th>Vencimiento</th>
                  <th>Días</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {proximas.map((l) => {
                  const est = estadoLicencia(l)
                  return (
                    <tr key={l.id}>
                      <td className="codigo-mono">{l.codigo}</td>
                      <td>{l.cliente}</td>
                      <td>{fecha(l.fecha_vencimiento)}</td>
                      <td className="num">{l.dias_restantes}</td>
                      <td>
                        <span className={`insignia insignia--${est.clase}`}>{est.etiqueta}</span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  )
}