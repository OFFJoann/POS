/** Campo de texto reutilizable. */
export default function Campo({ etiqueta, ayuda, error, children, obligatorio }) {
  return (
    <div className="campo">
      <label>
        {etiqueta}
        {obligatorio && <span style={{ color: 'var(--peligro)' }}> *</span>}
      </label>
      {children}
      {ayuda && <div className="campo__ayuda">{ayuda}</div>}
      {error && <div className="campo__ayuda" style={{ color: 'var(--peligro)' }}>{error}</div>}
    </div>
  )
}