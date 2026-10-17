/** Ventana modal genérica. */
import { useEffect } from 'react'

export default function Modal({ titulo, onCerrar, children, pie }) {
  useEffect(() => {
    const alPulsar = (e) => { if (e.key === 'Escape') onCerrar() }
    window.addEventListener('keydown', alPulsar)
    return () => window.removeEventListener('keydown', alPulsar)
  }, [onCerrar])

  return (
    <div className="modal-fondo" onClick={onCerrar}>
      <div
        className="modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="modal__cabecera">
          <h2>{titulo}</h2>
          <button type="button" className="cerrar" onClick={onCerrar} aria-label="Cerrar">
            ×
          </button>
        </div>
        <div className="modal__cuerpo">{children}</div>
        {pie && <div className="modal__pie">{pie}</div>}
      </div>
    </div>
  )
}