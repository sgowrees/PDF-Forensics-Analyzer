import type { AnalysisResponse } from '../types/analysis'
import { RiskBadge } from './RiskBadge'
import { ScoreBreakdown } from './ScoreBreakdown'

interface AnalysisReportProps {
  report: AnalysisResponse
  onReset: () => void
}

function basename(path: string | null): string | null {
  if (!path) return null
  const parts = path.replace(/\\/g, '/').split('/')
  return parts[parts.length - 1] || path
}

export function AnalysisReport({ report, onReset }: AnalysisReportProps) {
  const issues = report.reasons.filter((reason) => !reason.includes('(OK — text box)'))
  const allowed = report.reasons.filter((reason) => reason.includes('(OK — text box)'))

  return (
    <section className="report">
      <div className="report-header">
        <div>
          <p className="eyebrow">Analysis complete</p>
          <h2>{report.filename}</h2>
          <p className="meta">
            {report.doc_type.replace(/_/g, ' ')} · {report.issuer}
            {report.baseline_available && report.baseline_pdf_path && (
              <> · baseline: {basename(report.baseline_pdf_path)}</>
            )}
          </p>
        </div>
        <RiskBadge risk={report.risk} score={report.score} />
      </div>

      <div className="report-grid">
        <article className="card">
          <h3>Score breakdown</h3>
          <ScoreBreakdown breakdown={report.score_breakdown} />
        </article>

        <article className="card">
          <h3>Classification</h3>
          <dl className="facts">
            <div>
              <dt>Document type</dt>
              <dd>{report.doc_type.replace(/_/g, ' ')}</dd>
            </div>
            <div>
              <dt>Issuer</dt>
              <dd>{report.issuer}</dd>
            </div>
            <div>
              <dt>Confidence</dt>
              <dd>{(report.classification_confidence * 100).toFixed(1)}%</dd>
            </div>
            <div>
              <dt>Baseline matched</dt>
              <dd>{report.baseline_available ? 'Yes' : 'No'}</dd>
            </div>
          </dl>
        </article>
      </div>

      {issues.length > 0 && (
        <article className="card findings-card">
          <h3>Findings ({issues.length})</h3>
          <ul className="findings-list">
            {issues.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </article>
      )}

      {allowed.length > 0 && (
        <article className="card allowed-card">
          <h3>Allowed form changes ({allowed.length})</h3>
          <ul className="findings-list allowed">
            {allowed.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </article>
      )}

      {issues.length === 0 && allowed.length === 0 && (
        <article className="card clean-card">
          <h3>No issues detected</h3>
          <p className="muted">This document matched the baseline with no flagged changes.</p>
        </article>
      )}

      <button type="button" className="secondary-btn" onClick={onReset}>
        Analyze another file
      </button>
    </section>
  )
}
