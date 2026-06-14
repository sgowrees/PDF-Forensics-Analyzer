import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const me = await login(email, password)
      navigate(me.role === 'admin' ? '/admin' : '/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 420, margin: '80px auto', textAlign: 'center' }}>
      <h2>Login</h2>

      <form onSubmit={handleSubmit}>
        <input
          style={{ width: '100%', padding: 10, marginBottom: 10 }}
          placeholder="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <input
          style={{ width: '100%', padding: 10, marginBottom: 10 }}
          placeholder="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        <button style={{ width: '100%', padding: 10 }} disabled={loading}>
          {loading ? 'Logging in...' : 'Login'}
        </button>
      </form>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      <Link to="/register" style={{ display: 'inline-block', marginTop: 15 }}>
        Create account
      </Link>
    </div>
  )
}
