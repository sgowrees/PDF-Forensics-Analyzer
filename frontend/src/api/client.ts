const API_BASE = import.meta.env.VITE_API_URL ?? ''

export async function apiPost<T>(
  path: string,
  body: FormData,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    body,
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    const message =
      typeof data.error === 'string'
        ? data.error
        : Array.isArray(data.file)
          ? data.file.join(' ')
          : `Request failed (${response.status})`
    throw new Error(message)
  }

  return data as T
}
