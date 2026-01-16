/**
 * Base API client logic for Alfred
 */

interface FetchOptions extends RequestInit {
  params?: Record<string, string>
}

export async function fetchWithAuth(
  url: string,
  options: FetchOptions = {},
  token?: string,
) {
  const headers = new Headers(options.headers)

  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ message: 'Unknown error' }))
    throw new Error(
      error.message || `API request failed with status ${response.status}`,
    )
  }

  return response.json()
}
