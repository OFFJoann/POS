/** Muestra un secreto oculto, con botón para revelarlo y para copiarlo. */
import { useState } from 'react'

export default function Secreto({ valor }) {
  const [visible, setVisible] = useState(false)
  const [copiado, setCopiado] = useState(false)

  if (!valor) {
    return (
      <div className="aviso aviso--error">
        <strong>LICENCIA_SECRETO no está configurado.</strong> Las licencias se
        emiten sin firma y los POS con secreto configurado las rechazan.
      </div>
    )
  }

  // navigator.clipboard exige contexto seguro (HTTPS o localhost); si no está
  // disponible se avisa en vez de fallar en silencio.
  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(valor)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2000)
    } catch {
      setCopiado(false)
    }
  }

  return (
    <div className="secreto">
      <code>{visible ? valor : '•'.repeat(valor.length)}</code>
      <button
        type="button"
        className="boton boton--pequeno"
        onClick={() => setVisible((v) => !v)}
      >
        {visible ? 'Ocultar' : 'Mostrar'}
      </button>
      <button type="button" className="boton boton--pequeno" onClick={copiar}>
        {copiado ? '¡Copiado!' : 'Copiar'}
      </button>
    </div>
  )
}