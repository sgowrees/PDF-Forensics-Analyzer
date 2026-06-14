import { apiPost, setTokens } from './client'

export interface LoginResponse {
  access: string
  refresh: string
}

export async function login(email: string, password: string) {
  const data = await apiPost<LoginResponse>('/api/users/login/', {
    email,
    password,
  })

  setTokens(data.access, data.refresh)
  return data
}
