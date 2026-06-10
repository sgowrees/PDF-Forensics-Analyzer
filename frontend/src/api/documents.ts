import type { AnalysisResponse } from '../types/analysis'
import { apiPost } from './client'

export function uploadAndAnalyze(file: File): Promise<AnalysisResponse> {
  const form = new FormData()
  form.append('file', file)
  return apiPost<AnalysisResponse>('/api/documents/upload/', form)
}
