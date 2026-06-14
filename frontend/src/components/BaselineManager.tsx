import { useEffect, useRef, useState } from 'react'
import {
  deleteBaseline,
  listBaselines,
  uploadTemplate,
  type BaselineTemplate,
} from '../api/documents'

function formatBytes(bytes: number | null) {
  if (bytes === null) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function BaselineManager({
  onChange,
}: {
  onChange?: () => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [baselines, setBaselines] = useState<BaselineTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  async function loadBaselines() {
    setLoading(true)
    setError(null)

    try {
      const data = await listBaselines()
      setBaselines(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load baselines')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadBaselines()
  }, [])

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    setError(null)
    setMessage(null)

    try {
      await uploadTemplate(file)
      setMessage(`Added baseline: ${file.name}`)
      await loadBaselines()
      onChange?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  async function handleDelete(baseline: BaselineTemplate) {
    const confirmed = window.confirm(
      `Remove baseline "${baseline.filename}"? This cannot be undone.`
    )
    if (!confirmed) return

    setDeletingId(baseline.id)
    setError(null)
    setMessage(null)

    try {
      await deleteBaseline(baseline.id)
      setMessage(`Removed baseline: ${baseline.filename}`)
      await loadBaselines()
      onChange?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <section className="card admin-section">
      <div className="section-header">
        <div>
          <h2>Baseline templates</h2>
          <p className="muted">
            Trusted PDFs used for tamper comparison. Uploads are stored in the
            analysis catalog and can be removed at any time.
          </p>
        </div>

        <div>
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf,.pdf"
            hidden
            onChange={handleUpload}
          />
          <button
            className="secondary-btn"
            disabled={uploading}
            onClick={() => inputRef.current?.click()}
          >
            {uploading ? 'Uploading...' : '+ Add baseline'}
          </button>
        </div>
      </div>

      {message && <p className="success-banner">{message}</p>}
      {error && <div className="error-banner">{error}</div>}

      {loading && <p className="muted">Loading baselines...</p>}

      {!loading && baselines.length === 0 && (
        <p className="muted">No baselines yet. Add a trusted PDF to get started.</p>
      )}

      {!loading && baselines.length > 0 && (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Filename</th>
                <th>Size</th>
                <th>Uploaded by</th>
                <th>Added</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {baselines.map((baseline) => (
                <tr key={baseline.id}>
                  <td>{baseline.filename}</td>
                  <td>{formatBytes(baseline.file_size)}</td>
                  <td>{baseline.uploaded_by_email ?? 'System'}</td>
                  <td>{new Date(baseline.created_at).toLocaleString()}</td>
                  <td>
                    <button
                      className="danger-btn"
                      disabled={deletingId === baseline.id}
                      onClick={() => handleDelete(baseline)}
                    >
                      {deletingId === baseline.id ? 'Removing...' : 'Remove'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
