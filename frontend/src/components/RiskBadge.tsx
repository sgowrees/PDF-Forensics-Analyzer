import type { RiskLevel } from '../types/analysis'

interface RiskBadgeProps {
  risk: RiskLevel
  score: number
}

const STYLES: Record<RiskLevel, string> = {
  LOW: 'risk-low',
  MEDIUM: 'risk-medium',
  HIGH: 'risk-high',
}

export function RiskBadge({ risk, score }: RiskBadgeProps) {
  return (
    <div className={`risk-badge ${STYLES[risk]}`}>
      <span className="risk-label">{risk}</span>
      <span className="risk-score">{score}/100</span>
    </div>
  )
}
