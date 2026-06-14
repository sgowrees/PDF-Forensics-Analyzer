import { apiGet, apiPatch, apiPost } from './client'

export interface User {
  id: number
  username: string
  email: string
  role: 'admin' | 'user'
}

export interface RegisterResponse {
  id: number
  email: string
}

export interface DashboardStats {
  total_documents: number
  status_breakdown: Record<string, number>
  risk_breakdown: Record<string, number>
  total_users?: number
  total_baselines?: number
}

export interface AdminUser extends User {
  date_joined: string
  is_active: boolean
}

export async function register(email: string, password: string) {
  return apiPost<RegisterResponse>('/api/users/register/', {
    email,
    password,
  })
}

export async function getMe() {
  return apiGet<User>('/api/users/me/')
}

export async function getDashboard() {
  return apiGet<DashboardStats>('/api/users/dashboard/')
}

export async function listUsers() {
  return apiGet<AdminUser[]>('/api/users/admin/users/')
}

export async function updateUserRole(userId: number, role: 'admin' | 'user') {
  return apiPatch<AdminUser>(`/api/users/admin/users/${userId}/role/`, { role })
}
