import { useState } from 'react'
import { uploadAndAnalyze } from '../api/documents'
import { AnalysisReport } from '../components/AnalysisReport'
import { FileUpload } from '../components/FileUpload'
import type { AnalysisResponse } from '../types/analysis'

export default function UploadPage() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [report, setReport] = useState<AnalysisResponse | null>(null)

  async function handleUpload(file: File) {
    setLoading(true)
    setError(null)
    setReport(null)

    try {
      const result = await uploadAndAnalyze(file)
      setReport(result)
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

  return (
    <div className="app">
      <header className="header">
        <div>
          <p className="eyebrow">PDF Forensics</p>
          <h1>Document tamper analysis</h1>
          <p className="lede">
            Upload a PDF to compare it against trusted baselines and detect
            structural, text, and layout changes.
          </p>
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
      </main>
    </div>
  )
}