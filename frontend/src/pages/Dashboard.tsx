import { useEffect, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

export default function Dashboard() {
  const [data, setData] = useState<any>(null)

  useEffect(() => {
    fetch(`${API_BASE}/api/users/dashboard/`, {
      credentials: 'include',
    })
      .then(res => res.json())
      .then(setData)
  }, [])

  return (
    <div style={{ padding: 20 }}>
      <h1>Dashboard</h1>

      <p>Total documents: {data?.total_documents ?? 0}</p>
    </div>
  )
}