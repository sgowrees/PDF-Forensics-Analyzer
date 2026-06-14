import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { listDocuments, uploadAndAnalyze, getDocument, type DocumentSummary } from '../api/documents'
import { FileUpload } from '../components/FileUpload'
import { AnalysisReport } from '../components/AnalysisReport'
import type { AnalysisResponse } from '../types/analysis'

function documentToReport(
  doc: DocumentSummary,
  analysis?: {
    score: number
    risk: string
    reasons: string[]
    score_breakdown: Record<string, number>
    baseline_available: boolean
    classification_confidence: number
  } | null
): AnalysisResponse | null {
  if (!doc.risk || doc.score === null) return null

  return {
    document_id: doc.id,
    status: doc.status,
    filename: doc.original_filename,
    doc_type: doc.doc_type,
    issuer: doc.issuer,
    issuer_slug: '',
    score: analysis?.score ?? doc.score,
    risk: (analysis?.risk ?? doc.risk) as AnalysisResponse['risk'],
    reasons: analysis?.reasons ?? [],
    score_breakdown: analysis?.score_breakdown ?? {},
    baseline_available: analysis?.baseline_available ?? false,
    baseline_pdf_path: null,
    classification_confidence: analysis?.classification_confidence ?? 0,
  }
}

export default function UserDashboard() {
  const { user, logout } = useAuth()

  const [loading, setLoading] = useState(false)
  const [historyLoading, setHistoryLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [report, setReport] = useState<AnalysisResponse | null>(null)
  const [history, setHistory] = useState<DocumentSummary[]>([])

  async function loadHistory() {
    setHistoryLoading(true)
    try {
      const docs = await listDocuments()
      setHistory(docs)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load history')
    } finally {
      setHistoryLoading(false)
    }
  }

  useEffect(() => {
    loadHistory()
  }, [])

  async function handleUpload(file: File) {
    setLoading(true)
    setError(null)
    setReport(null)

    try {
      const result = await uploadAndAnalyze(file)
      setReport(result)
      await loadHistory()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  function handleReset() {
    setReport(null)
    setError(null)
  }

  async function handleViewPast(doc: DocumentSummary) {
    try {
      const detail = await getDocument(doc.id)
      const pastReport = documentToReport(doc, detail.analysis)
      if (pastReport) {
        setReport(pastReport)
        setError(null)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load result')
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div>
          <p className="eyebrow">PDF Forensics</p>
          <h1>Document tamper analysis</h1>
          <p className="lede">
            Upload a PDF to compare it against trusted baselines.
          </p>

          <div style={{ marginTop: 10 }}>
            <strong>{user?.email}</strong>
            <button onClick={logout} style={{ marginLeft: 10 }}>
              Logout
            </button>
            {user?.role === 'admin' && (
              <Link to="/admin" style={{ marginLeft: 10 }}>
                Admin dashboard
              </Link>
            )}
          </div>
        </div>
      </header>

      <main className="main">
        {!report && (
          <>
            <FileUpload onUpload={handleUpload} loading={loading} />
            {error && <div className="error-banner">{error}</div>}
          </>
        )}

        {report && (
          <AnalysisReport report={report} onReset={handleReset} />
        )}

        <section style={{ marginTop: 40 }}>
          <h2>Past results</h2>

          {historyLoading && <p>Loading history...</p>}

          {!historyLoading && history.length === 0 && (
            <p>No analyses yet. Upload a PDF to get started.</p>
          )}

          {!historyLoading && history.length > 0 && (
            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 12 }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', padding: 8 }}>File</th>
                  <th style={{ textAlign: 'left', padding: 8 }}>Status</th>
                  <th style={{ textAlign: 'left', padding: 8 }}>Risk</th>
                  <th style={{ textAlign: 'left', padding: 8 }}>Score</th>
                  <th style={{ textAlign: 'left', padding: 8 }}>Date</th>
                  <th style={{ textAlign: 'left', padding: 8 }}></th>
                </tr>
              </thead>
              <tbody>
                {history.map((doc) => (
                  <tr key={doc.id} style={{ borderTop: '1px solid #ddd' }}>
                    <td style={{ padding: 8 }}>{doc.original_filename}</td>
                    <td style={{ padding: 8 }}>{doc.status}</td>
                    <td style={{ padding: 8 }}>{doc.risk ?? '—'}</td>
                    <td style={{ padding: 8 }}>{doc.score ?? '—'}</td>
                    <td style={{ padding: 8 }}>
                      {new Date(doc.created_at).toLocaleString()}
                    </td>
                    <td style={{ padding: 8 }}>
                      {doc.risk && (
                        <button onClick={() => handleViewPast(doc)}>
                          View
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </main>
    </div>
  )
}
