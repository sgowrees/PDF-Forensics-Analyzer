export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH'

export interface ScoreBreakdown {
  comparison?: number
  signatures?: number
  images?: number
  layout?: number
  text?: number
  metadata?: number
}

export interface AnalysisResponse {
  document_id: string
  status: string
  filename: string
  doc_type: string
  issuer: string
  issuer_slug: string
  score: number
  risk: RiskLevel
  reasons: string[]
  score_breakdown: ScoreBreakdown
  baseline_available: boolean
  baseline_pdf_path: string | null
  classification_confidence: number
}

export interface ApiError {
  error?: string
  file?: string[]
  detail?: string
}
