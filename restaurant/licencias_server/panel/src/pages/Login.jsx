/** Pantalla de acceso al panel. */
import { useState } from 'react'
import { useSesion } from '../hooks/useSesion'

export default function Login() {
  const { login } = useSesion()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [enviando, setEnviando] = useState(false)

  const enviar = async (e) => {
    e.preventDefault()
    setEnviando(true)
    setError(null)
    try {
      await login(username.trim(), password)
    } catch (err) {
      setError(err.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="login">
      <div className="login__caja">
        <h1>Panel de Licencias</h1>
        <p className="sub">Servidor central de TorreApp</p>

        {error && <div className="aviso aviso--error">{error}</div>}

        <form onSubmit={enviar}>
          <div className="campo">
            <label htmlFor="u">Usuario</label>
            <input
              id="u"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              autoFocus
              required
            />
          </div>
          <div className="campo">
            <label htmlFor="p">Contraseña</label>
            <input
              id="p"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>
          <button
            type="submit"
            className="boton boton--primario"
            style={{ width: '100%', justifyContent: 'center' }}
            disabled={enviando}
          >
            {enviando ? 'Entrando…' : 'Entrar'}
          </button>
        </form>
      </div>
    </div>
  )
}