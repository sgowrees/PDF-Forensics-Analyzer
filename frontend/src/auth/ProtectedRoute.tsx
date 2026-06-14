import { Navigate } from 'react-router-dom'
import { useAuth } from './AuthContext'

export default function ProtectedRoute({
  children,
}: {
  children: React.ReactNode
}) {
  const { user, loading } = useAuth()

  if (loading) return <p>Loading...</p>
  if (!user) return <Navigate to="/login" replace />

  return <>{children}</>
}

export function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()

  if (loading) return <p>Loading...</p>
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== 'admin') return <Navigate to="/dashboard" replace />

  return <>{children}</>
}
