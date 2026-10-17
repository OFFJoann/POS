/** Formulario de alta/edición de una licencia. */
import { useState } from 'react'
import Campo from './Campo'
import Secreto from './Secreto'
import { useConfiguracion } from '../hooks/useConfiguracion'
import { fecha, limiteTexto, vencimientoPorDefecto } from '../utils/formato'

const VACIO = {
  codigo: '',
  cliente: '',
  fecha_inicio: new Date().toISOString().slice(0, 10),
  fecha_vencimiento: vencimientoPorDefecto(),
  limite_vendedores: 5,
  mensualidad: '',
  activa: true,
}

export default function FormularioLicencia({ licencia, alGuardar, onCancelar, guardando, error }) {
  const [datos, setDatos] = useState(
    licencia
      ? {
          codigo: licencia.codigo,
          cliente: licencia.cliente,
          fecha_inicio: licencia.fecha_inicio,
          fecha_vencimiento: licencia.fecha_vencimiento,
          limite_vendedores: licencia.limite_vendedores,
          mensualidad: licencia.mensualidad,
          activa: licencia.activa,
        }
      : VACIO,
  )
  const { configuracion } = useConfiguracion()

  const cambiar = (campo) => (e) => {
    const valor = e.target.type === 'checkbox' ? e.target.checked : e.target.value
    setDatos((d) => ({ ...d, [campo]: valor }))
  }

  const enviar = (e) => {
    e.preventDefault()
    alGuardar({
      ...datos,
      limite_vendedores: Number(datos.limite_vendedores) || 0,
      // Vacío o basura se manda tal cual: el backend lo valida y avisa.
      mensualidad: datos.mensualidad,
    })
  }

  return (
    <form onSubmit={enviar}>
      {error && <div className="aviso aviso--error">{error}</div>}

      <Campo etiqueta="Código" ayuda="Lo usa el POS en LICENCIA_CODIGO. Se guarda en mayúsculas." obligatorio>
        <input
          value={datos.codigo}
          onChange={cambiar('codigo')}
          placeholder="ELCHOLI-DEMO"
          required
        />
      </Campo>

      <Campo etiqueta="Cliente" ayuda="Nombre del negocio licenciado." obligatorio>
        <input
          value={datos.cliente}
          onChange={cambiar('cliente')}
          placeholder="El Choli"
          required
        />
      </Campo>

      <div className="rejilla rejilla--2">
        <Campo etiqueta="Inicio de vigencia">
          <input type="date" value={datos.fecha_inicio} onChange={cambiar('fecha_inicio')} />
        </Campo>

        <Campo etiqueta="Vencimiento" ayuda="Último día de validez, inclusive." obligatorio>
          <input
            type="date"
            value={datos.fecha_vencimiento}
            onChange={cambiar('fecha_vencimiento')}
            required
          />
        </Campo>
      </div>

      <Campo etiqueta="Límite de vendedores" ayuda="Máximo de vendedores activos. 0 = sin límite.">
        <input
          type="number"
          min="0"
          value={datos.limite_vendedores}
          onChange={cambiar('limite_vendedores')}
        />
        <div className="campo__ayuda">
          Actual: {limiteTexto(Number(datos.limite_vendedores) || 0)}
        </div>
      </Campo>

      <Campo
        etiqueta="Mensualidad"
        ayuda="Lo que paga el cliente cada mes. El resumen suma las licencias activas para dar el ingreso mensual."
      >
        <input
          type="number"
          min="0"
          step="0.01"
          inputMode="decimal"
          placeholder="0.00"
          value={datos.mensualidad}
          onChange={cambiar('mensualidad')}
        />
      </Campo>

      <div className="campo campo--checkbox">
        <input id="activa" type="checkbox" checked={datos.activa} onChange={cambiar('activa')} />
        <label htmlFor="activa">Licencia activa (si la desmarcas, el POS la rechaza)</label>
      </div>

      {licencia && (
        <div className="campo__ayuda" style={{ marginBottom: 14 }}>
          Creada el {fecha(licencia.creada_en)} · actualizada el {fecha(licencia.actualizada_en)}
        </div>
      )}

      {/*
        Al editar se muestra el secreto compartido: es lo que hay que copiar
        al .env del POS junto con el código. Solo aparece si la configuración
        (privada, de superusuario) ya llegó; mientras carga no se dibuja nada.
      */}
      {licencia && configuracion && (
        <div className="bloque-secreto">
          <div className="bloque-secreto__titulo">
            Secreto de firma que necesita este POS
          </div>
          <div className="campo__ayuda" style={{ marginBottom: 8 }}>
            En el <code>.env</code> del cliente van estas dos líneas:
            <br />
            <code>LICENCIA_CODIGO={licencia.codigo}</code>
            <br />
            <code>LICENCIA_SECRETO=…</code> (el de abajo, con «Mostrar» o «Copiar»)
            <br />
            El secreto es el mismo para todas las licencias; si no coincide, el
            POS rechaza la licencia por firma inválida.
          </div>
          <Secreto valor={configuracion.secreto} />
        </div>
      )}

      <div className="fila-acciones" style={{ justifyContent: 'flex-end' }}>
        <button type="button" className="boton" onClick={onCancelar} disabled={guardando}>
          Cancelar
        </button>
        <button type="submit" className="boton boton--primario" disabled={guardando}>
          {guardando ? 'Guardando…' : licencia ? 'Guardar cambios' : 'Crear licencia'}
        </button>
      </div>
    </form>
  )
}