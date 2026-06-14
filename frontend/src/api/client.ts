export const API_BASE =
  import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem('access')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const isFormData = options.body instanceof FormData

  const res = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...getAuthHeaders(),
      ...(options.headers || {}),
    },
  })

  const data = await res.json().catch(() => ({}))

  if (!res.ok) {
    const message =
      data?.detail ||
      data?.error ||
      (typeof data === 'object' ? Object.values(data).flat().join(', ') : null) ||
      'Request failed'
    throw new Error(message)
  }

  return data as T
}

export function apiPost<T>(url: string, body?: unknown): Promise<T> {
  return request<T>(url, {
    method: 'POST',
    body: body === undefined ? undefined : JSON.stringify(body),
  })
}

export function apiGet<T>(url: string): Promise<T> {
  return request<T>(url, { method: 'GET' })
}

export function apiDelete<T>(url: string): Promise<T> {
  return request<T>(url, { method: 'DELETE' })
}

export function apiPatch<T>(url: string, body: unknown): Promise<T> {
  return request<T>(url, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export function clearTokens() {
  localStorage.removeItem('access')
  localStorage.removeItem('refresh')
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem('access', access)
  localStorage.setItem('refresh', refresh)
}

export function apiUpload<T>(url: string, formData: FormData): Promise<T> {
  return request<T>(url, {
    method: 'POST',
    body: formData,
  })
}
