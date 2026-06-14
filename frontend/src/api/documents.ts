import { apiDelete, apiGet, apiUpload } from './client'
import type { AnalysisResponse } from '../types/analysis'

export interface DocumentSummary {
  id: string
  original_filename: string
  doc_type: string
  issuer: string
  status: string
  risk: string | null
  score: number | null
  owner_email?: string | null
  created_at: string
}

export interface BaselineTemplate {
  id: number
  name: string
  filename: string
  file_size: number | null
  uploaded_by_email: string | null
  created_at: string
}

export interface DocumentDetail extends DocumentSummary {
  issuer_slug: string
  updated_at: string
  analysis: {
    score: number
    risk: string
    baseline_available: boolean
    reasons: string[]
    score_breakdown: Record<string, number>
    classification_confidence: number
    created_at: string
  } | null
}

export async function uploadAndAnalyze(file: File) {
  const formData = new FormData()
  formData.append('file', file)

  return apiUpload<AnalysisResponse>('/api/documents/upload/', formData)
}

export async function uploadTemplate(file: File) {
  const formData = new FormData()
  formData.append('file', file)

  return apiUpload<BaselineTemplate>('/api/documents/templates/upload/', formData)
}

export async function listBaselines() {
  return apiGet<BaselineTemplate[]>('/api/documents/templates/')
}

export async function deleteBaseline(id: number) {
  return apiDelete(`/api/documents/templates/${id}/`)
}

export async function listDocuments() {
  return apiGet<DocumentSummary[]>('/api/documents/')
}

export async function getDocument(id: string) {
  return apiGet<DocumentDetail>(`/api/documents/${id}/`)
}
