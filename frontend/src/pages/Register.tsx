import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { register } from '../api/users'

export default function Register() {
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
      await register(email, password)
      navigate('/login')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 420, margin: '80px auto', textAlign: 'center' }}>
      <h2>Register</h2>

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
          placeholder="Password (min 8 characters)"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          minLength={8}
          required
        />

        <button style={{ width: '100%', padding: 10 }} disabled={loading}>
          {loading ? 'Creating...' : 'Register'}
        </button>
      </form>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      <Link to="/login" style={{ display: 'inline-block', marginTop: 15 }}>
        Back to login
      </Link>
    </div>
  )
}
