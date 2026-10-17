/** Indicador de carga con spinner. */
export default function Cargando({ texto = 'Cargando…' }) {
  return (
    <div className="vacio" role="status" aria-live="polite">
      <span
        className="girador"
        style={{ display: 'inline-block', verticalAlign: -3, marginRight: 9 }}
      />
      {texto}
    </div>
  )
}