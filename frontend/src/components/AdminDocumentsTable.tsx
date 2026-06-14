import { useEffect, useState } from 'react'
import { listDocuments, type DocumentSummary } from '../api/documents'

export default function AdminDocumentsTable() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listDocuments()
      .then(setDocuments)
      .catch((err) =>
        setError(err instanceof Error ? err.message : 'Failed to load documents')
      )
      .finally(() => setLoading(false))
  }, [])

  return (
    <section className="card admin-section">
      <div className="section-header">
        <div>
          <h2>All analyses</h2>
          <p className="muted">Every document analyzed across all user accounts.</p>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}
      {loading && <p className="muted">Loading analyses...</p>}

      {!loading && documents.length === 0 && (
        <p className="muted">No documents analyzed yet.</p>
      )}

      {!loading && documents.length > 0 && (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>File</th>
                <th>User</th>
                <th>Type</th>
                <th>Issuer</th>
                <th>Status</th>
                <th>Risk</th>
                <th>Score</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id}>
                  <td>{doc.original_filename}</td>
                  <td>{doc.owner_email ?? '—'}</td>
                  <td>{doc.doc_type}</td>
                  <td>{doc.issuer || '—'}</td>
                  <td>{doc.status}</td>
                  <td>{doc.risk ?? '—'}</td>
                  <td>{doc.score ?? '—'}</td>
                  <td>{new Date(doc.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
