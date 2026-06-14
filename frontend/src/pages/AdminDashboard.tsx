import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { getDashboard, type DashboardStats } from '../api/users'
import BaselineManager from '../components/BaselineManager'
import AdminDocumentsTable from '../components/AdminDocumentsTable'

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="stat-card">
      <p className="stat-label">{label}</p>
      <p className="stat-value">{value}</p>
    </div>
  )
}

export default function AdminDashboard() {
  const { user, logout } = useAuth()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function loadStats() {
    try {
      const data = await getDashboard()
      setStats(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load stats')
    }
  }

  useEffect(() => {
    loadStats()
  }, [])

  return (
    <div className="app admin-app">
      <header className="header">
        <div>
          <p className="eyebrow">PDF Forensics</p>
          <h1>Admin dashboard</h1>
          <p className="lede">
            Manage baseline templates, users, and review system-wide analysis activity.
          </p>

          <div className="header-actions">
            <strong>{user?.email}</strong>
            <button onClick={logout}>Logout</button>
            <Link to="/dashboard">User dashboard</Link>
          </div>
        </div>
      </header>

      <main className="main admin-main">
        {error && <div className="error-banner">{error}</div>}

        {stats && (
          <section className="stats-grid">
            <StatCard label="Documents" value={stats.total_documents} />
            <StatCard label="Users" value={stats.total_users ?? 0} />
            <StatCard label="Baselines" value={stats.total_baselines ?? 0} />
            <StatCard label="High risk" value={stats.risk_breakdown.HIGH ?? 0} />
          </section>
        )}

        <BaselineManager onChange={loadStats} />
        <AdminDocumentsTable />
      </main>
    </div>
  )
}
