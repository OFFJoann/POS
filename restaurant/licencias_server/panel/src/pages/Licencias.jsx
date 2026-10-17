/** Módulo Licencias: listado, filtros y acciones masivas. */
import { useCallback, useEffect, useMemo, useState } from 'react'
import Cargando from '../components/Cargando'
import {
  listarLicencias,
  crearLicencia,
  actualizarLicencia,
  eliminarLicencia,
  ejecutarAcciones,
} from '../api/licencias'
import { useConfiguracion } from '../hooks/useConfiguracion'
import {
  fechaCorta,
  estadoLicencia,
  limiteTexto,
  dinero,
  tocaCobrar,
  trasDias,
  DIAS_MENSUALIDAD,
} from '../utils/formato'
import FormularioLicencia from '../components/FormularioLicencia'
import Modal from '../components/Modal'

const FILTROS = [
  { valor: '', texto: 'Todas' },
  { valor: 'activas', texto: 'Activas' },
  { valor: 'pausadas', texto: 'Pausadas' },
  { valor: 'por_vencer', texto: 'Vencen en 30 días' },
  { valor: 'vencidas', texto: 'Vencidas' },
  { valor: 'por_cobrar', texto: 'Pendientes de cobro' },
]

const TITULOS_ACCION = {
  mensualidad: 'Actualizar mensualidad',
  extender: 'Extender vencimiento',
}

const EXPLICACION_ACCION = {
  extender: 'Se suman los días indicados a la fecha de vencimiento actual.',
}

export default function PaginaLicencias() {
  const [licencias, setLicencias] = useState([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState(null)
  const [aviso, setAviso] = useState(null)
  const [busqueda, setBusqueda] = useState('')
  const [filtro, setFiltro] = useState('')
  const [seleccion, setSeleccion] = useState([])
  const [editando, setEditando] = useState(null)
  const [creando, setCreando] = useState(false)
  const [porEliminar, setPorEliminar] = useState(null)
  const [guardando, setGuardando] = useState(false)
  const [errorForm, setErrorForm] = useState(null)
  const [confirmando, setConfirmando] = useState(null)
  const [aplicando, setAplicando] = useState(false)
  const { recargar: recargarConfig } = useConfiguracion()

  const cargar = useCallback(async () => {
    setCargando(true)
    try {
      const datos = await listarLicencias({ q: busqueda, estado: filtro })
      setLicencias(datos.licencias)
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setCargando(false)
    }
  }, [busqueda, filtro])

  useEffect(() => {
    const t = setTimeout(cargar, busqueda ? 300 : 0)
    return () => clearTimeout(t)
  }, [cargar, busqueda])

  const todasSeleccionadas =
    licencias.length > 0 && seleccion.length === licencias.length

  const alternarTodas = () => {
    setSeleccion(todasSeleccionadas ? [] : licencias.map((l) => l.id))
  }

  const alternarUna = (id) => {
    setSeleccion((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]))
  }

  const guardar = async (datos) => {
    setGuardando(true)
    setErrorForm(null)
    try {
      if (editando) {
        await actualizarLicencia(editando.id, datos)
        setAviso(`Licencia ${datos.codigo} actualizada.`)
      } else {
        await crearLicencia(datos)
        setAviso(`Licencia ${datos.codigo} creada.`)
      }
      setEditando(null)
      setCreando(false)
      await cargar()
      recargarConfig()
    } catch (e) {
      setErrorForm(e.message)
    } finally {
      setGuardando(false)
    }
  }

  const borrar = async () => {
    try {
      await eliminarLicencia(porEliminar.id)
      setAviso(`Licencia ${porEliminar.codigo} eliminada.`)
      setPorEliminar(null)
      await cargar()
      recargarConfig()
    } catch (e) {
      setError(e.message)
      setPorEliminar(null)
    }
  }

  const ejecutar = async (nombre, ids, extra = {}) => {
    if (aplicando) return
    setAplicando(true)
    try {
      const r = await ejecutarAcciones(ids, nombre, extra)
      setAviso(`${r.procesadas} licencia(s): ${r.detalles.join(', ')}`)
      setSeleccion([])
      await cargar()
      recargarConfig()
    } catch (e) {
      setError(e.message)
    } finally {
      setAplicando(false)
    }
  }

  /**
   * Decide si la acción se pide confirmada o se aplica de una vez.
   *
   * Extender meses cambia el vencimiento y desde el panel no hay vuelta atrás,
   * así que un doble clic cobraría dos meses: primero se muestra a quién y hasta
   * qué fecha. Pausar y reactivar son reversibles y no mueven la facturación,
   * así que se aplican directos como antes.
   */
  const pedirAccion = (nombre, ids, extra = {}) => {
    if (!ids.length || aplicando) return
    if (nombre === 'pausar' || nombre === 'reactivar') {
      ejecutar(nombre, ids, extra)
      return
    }
    setConfirmando({
      accion: nombre,
      ids,
      extra,
      hoy: new Date().toISOString().slice(0, 10),
    })
  }

  const confirmar = async () => {
    const pendiente = confirmando
    if (!pendiente) return
    setConfirmando(null)
    await ejecutar(pendiente.accion, pendiente.ids, pendiente.extra)
  }

  const contadorSeleccion = useMemo(() => seleccion.length, [seleccion])

  // Suma de lo que se está viendo ahora mismo, para no tener que filtrar a mano.
  const totalMensual = useMemo(
    () => licencias.reduce((suma, l) => suma + (Number(l.mensualidad) || 0), 0),
    [licencias],
  )

  // Licencias a las que ya les toca cobrar el mes: vencen en 30 días o menos,
  // están pausadas o ya vencieron. Se marcan para no pasarlas por alto.
  const paraCobrar = useMemo(() => licencias.filter(tocaCobrar), [licencias])

  // Datos del diálogo de confirmación: a quién toca y hasta qué fecha quedaría.
  // `hoy` se fija al abrir el diálogo, no en cada render, para que la vista
  // previa use el día real aunque el panel lleve horas abierto.
  const afectadas = useMemo(
    () => (confirmando ? licencias.filter((l) => confirmando.ids.includes(l.id)) : []),
    [confirmando, licencias],
  )
  const hoyIso = confirmando?.hoy ?? ''
  const diasAccion =
    confirmando?.accion === 'mensualidad'
      ? DIAS_MENSUALIDAD
      : (confirmando?.extra?.dias ?? 0)

  return (
    <>
      <div className="encabezado">
        <div>
          <h1>Licencias</h1>
          <p>Emite, renueva y pausa las licencias de los POS.</p>
        </div>
        <button type="button" className="boton boton--primario" onClick={() => setCreando(true)}>
          + Nueva licencia
        </button>
      </div>

      {aviso && (
        <div className="aviso aviso--ok">
          {aviso}
          <button
            type="button"
            className="cerrar"
            style={{ float: 'right', marginTop: -4 }}
            onClick={() => setAviso(null)}
            aria-label="Cerrar"
          >
            ×
          </button>
        </div>
      )}
      {error && <div className="aviso aviso--error">{error}</div>}

      <div className="barra-filtros">
        <input
          type="search"
          placeholder="Buscar por código o cliente…"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
        />
        <select value={filtro} onChange={(e) => setFiltro(e.target.value)}>
          {FILTROS.map((f) => (
            <option key={f.valor} value={f.valor}>{f.texto}</option>
          ))}
        </select>
        {!filtro && paraCobrar.length > 0 && (
          <button
            type="button"
            className="boton boton--pequeno boton--cobrar"
            onClick={() => pedirAccion('mensualidad', paraCobrar.map((l) => l.id))}
            disabled={aplicando}
            title={`Actualizar mensualidad de las ${paraCobrar.length} pendientes`}
          >
            {paraCobrar.length} por cobrar
          </button>
        )}
        {contadorSeleccion > 0 && (
          <>
            <span style={{ color: 'var(--texto-suave)', fontSize: 14 }}>
              {contadorSeleccion} seleccionada(s)
            </span>
            <button
              type="button"
              className="boton boton--primario boton--pequeno"
              disabled={aplicando}
              onClick={() => pedirAccion('mensualidad', seleccion)}
              title={`Suma ${DIAS_MENSUALIDAD} días y reactiva`}
            >
              Actualizar mensualidad
            </button>
            <button type="button" className="boton boton--pequeno" disabled={aplicando} onClick={() => pedirAccion('extender', seleccion, { dias: 30 })}>
              +30 días
            </button>
            <button type="button" className="boton boton--pequeno" disabled={aplicando} onClick={() => pedirAccion('extender', seleccion, { dias: 60 })}>
              +60 días
            </button>
            <button type="button" className="boton boton--pequeno" disabled={aplicando} onClick={() => pedirAccion('extender', seleccion, { dias: 90 })}>
              +90 días
            </button>
            <button type="button" className="boton boton--pequeno" disabled={aplicando} onClick={() => pedirAccion('reactivar', seleccion)}>
              Reactivar
            </button>
            <button type="button" className="boton boton--peligro boton--pequeno" disabled={aplicando} onClick={() => pedirAccion('pausar', seleccion)}>
              Pausar
            </button>
          </>
        )}
      </div>

      <div className="tarjeta">
        {cargando ? (
          <Cargando />
        ) : licencias.length === 0 ? (
          <div className="vacio">
            {busqueda || filtro
              ? 'Ninguna licencia coincide con el filtro.'
              : 'Todavía no hay licencias. Crea la primera con «+ Nueva licencia».'}
          </div>
        ) : (
          <div className="tabla-envoltura">
            <table className="tabla">
              <thead>
                <tr>
                  <th style={{ width: 34 }}>
                    <input
                      type="checkbox"
                      checked={todasSeleccionadas}
                      onChange={alternarTodas}
                      aria-label="Seleccionar todas"
                    />
                  </th>
                  <th>Código</th>
                  <th>Cliente</th>
                  <th>Vencimiento</th>
                  <th className="num">Días</th>
                  <th className="num">Vendedores</th>
                  <th className="num">Mensualidad</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {licencias.map((l) => {
                  const est = estadoLicencia(l)
                  return (
                    <tr key={l.id}>
                      <td>
                        <input
                          type="checkbox"
                          checked={seleccion.includes(l.id)}
                          onChange={() => alternarUna(l.id)}
                          aria-label={`Seleccionar ${l.codigo}`}
                        />
                      </td>
                      <td className="codigo-mono">{l.codigo}</td>
                      <td>{l.cliente}</td>
                      <td>{fechaCorta(l.fecha_vencimiento)}</td>
                      <td className="num">{l.dias_restantes}</td>
                      <td className="num">{limiteTexto(l.limite_vendedores)}</td>
                      <td className="num">
                        {Number(l.mensualidad) > 0 ? dinero(l.mensualidad) : '—'}
                      </td>
                      <td>
                        <span className={`insignia insignia--${est.clase}`}>{est.etiqueta}</span>
                      </td>
                      <td>
                        <div className="fila-acciones">
                          <button
                            type="button"
                            className={`boton boton--pequeno ${tocaCobrar(l) ? 'boton--cobrar' : ''}`}
                            disabled={aplicando}
                            title={`Actualizar mensualidad: +${DIAS_MENSUALIDAD} días y reactiva`}
                            aria-label={`Actualizar mensualidad de ${l.codigo}`}
                            onClick={() => pedirAccion('mensualidad', [l.id])}
                          >
                            Mensualidad
                          </button>
                          <button
                            type="button"
                            className="boton boton--pequeno"
                            disabled={aplicando}
                            onClick={() => { setErrorForm(null); setEditando(l) }}
                          >
                            Editar
                          </button>
                          <button
                            type="button"
                            className="boton boton--peligro boton--pequeno"
                            disabled={aplicando}
                            onClick={() => setPorEliminar(l)}
                          >
                            Eliminar
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
              {totalMensual > 0 && (
                <tfoot>
                  <tr>
                    <td colSpan={6}>
                      Suma de las {licencias.length} licencias de esta vista
                    </td>
                    <td className="num"><strong>{dinero(totalMensual)}</strong></td>
                    <td colSpan={2} />
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        )}
      </div>

      {(creando || editando) && (
        <Modal
          titulo={editando ? `Editar ${editando.codigo}` : 'Nueva licencia'}
          onCerrar={() => { setCreando(false); setEditando(null); setErrorForm(null) }}
        >
          <FormularioLicencia
            licencia={editando}
            alGuardar={guardar}
            onCancelar={() => { setCreando(false); setEditando(null); setErrorForm(null) }}
            guardando={guardando}
            error={errorForm}
          />
        </Modal>
      )}

      {porEliminar && (
        <Modal
          titulo="Eliminar licencia"
          onCerrar={() => setPorEliminar(null)}
          pie={
            <>
              <button type="button" className="boton" onClick={() => setPorEliminar(null)}>
                Cancelar
              </button>
              <button type="button" className="boton boton--peligro" onClick={borrar}>
                Eliminar definitivamente
              </button>
            </>
          }
        >
          <p>
            ¿Eliminar <strong>{porEliminar.codigo}</strong> ({porEliminar.cliente})?
          </p>
          <p style={{ color: 'var(--texto-suave)', fontSize: 14 }}>
            El POS dejará de validar esta licencia en su próxima consulta. Si solo
            quieres detenerla temporalmente, usa <strong>Pausar</strong>.
          </p>
        </Modal>
      )}
    {confirmando && (
        <Modal
          titulo={TITULOS_ACCION[confirmando.accion]}
          onCerrar={() => !aplicando && setConfirmando(null)}
          pie={
            <>
              <button
                type="button"
                className="boton"
                disabled={aplicando}
                onClick={() => setConfirmando(null)}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="boton boton--primario"
                disabled={aplicando}
                onClick={confirmar}
              >
                {aplicando ? 'Aplicando…' : `Sí, ${TITULOS_ACCION[confirmando.accion]}`}
              </button>
            </>
          }
        >
          <p>
            {confirmando.ids.length === 1
              ? 'Esta licencia:'
              : `Estas ${confirmando.ids.length} licencias:`}
          </p>
          <ul className="lista-confirmacion">
            {afectadas.map((l) => (
              <li key={l.id}>
                <div>
                  <strong>{l.cliente}</strong> <span className="codigo-mono">{l.codigo}</span>
                </div>
                <div className="lista-confirmacion__fechas">
                  <span className="lista-confirmacion__antes">{fechaCorta(l.fecha_vencimiento)}</span>
                  <span aria-hidden="true">→</span>
                  <strong>{fechaCorta(trasDias(
                    l.fecha_vencimiento >= hoyIso ? l.fecha_vencimiento : hoyIso,
                    diasAccion,
                  ))}</strong>
                </div>
              </li>
            ))}
          </ul>
          <p className="lista-confirmacion__nota">
            {confirmando.accion === 'mensualidad'
              ? 'Registra que el mes ya está pagado. La licencia queda activa y el POS vuelve a aceptarla.'
              : EXPLICACION_ACCION[confirmando.accion]}
          </p>
          <p className="lista-confirmacion__nota lista-confirmacion__nota--fuerte">
            No hay forma de revertirlo desde el panel: revisa antes de confirmar.
          </p>
        </Modal>
      )}
    </>
  )
}