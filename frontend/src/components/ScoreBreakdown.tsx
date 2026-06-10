import type { ScoreBreakdown as Breakdown } from '../types/analysis'

const LABELS: Record<string, string> = {
  comparison: 'Baseline comparison',
  signatures: 'Signatures',
  images: 'Images',
  layout: 'Layout',
  text: 'Text',
  metadata: 'Metadata',
}

interface ScoreBreakdownProps {
  breakdown: Breakdown
}

export function ScoreBreakdown({ breakdown }: ScoreBreakdownProps) {
  const entries = Object.entries(breakdown).filter(([, value]) => value > 0)

  if (entries.length === 0) {
    return <p className="muted">No score contributions from individual checks.</p>
  }

  const max = Math.max(...entries.map(([, value]) => value), 1)

  return (
    <ul className="breakdown-list">
      {entries.map(([key, value]) => (
        <li key={key} className="breakdown-item">
          <div className="breakdown-header">
            <span>{LABELS[key] ?? key}</span>
            <span>{value}</span>
          </div>
          <div className="breakdown-bar">
            <div
              className="breakdown-fill"
              style={{ width: `${(value / max) * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  )
}
