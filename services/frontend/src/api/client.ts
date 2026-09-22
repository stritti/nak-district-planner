import { useAuthStore } from '../stores/auth'
import { useOIDC } from '../composables/useOIDC'
import { useCSRF } from '../composables/useCSRF'
import { router } from '../router'

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const authStore = useAuthStore()
  const { getCSRFHeaders } = useCSRF()
  const oidc = useOIDC(router)

  // If the access token already expired (e.g. the scheduled refresh timer
  // was throttled while the tab was backgrounded), refresh it up front
  // instead of firing an unauthenticated request that is bound to 401.
  if (authStore.token && authStore.isTokenExpired) {
    const refreshed = await oidc.refreshToken()
    if (!refreshed) {
      throw new Error('Unauthorized - please log in again')
    }
  }

  const initiatingGeneration = oidc.getSessionGeneration()

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  const token = authStore.getToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  // Add CSRF token for state-changing requests
  const csrfHeaders = getCSRFHeaders()
  Object.assign(headers, csrfHeaders)

  let res = await fetch(path, {
    ...options,
    headers,
  })

  if (res.status === 401 && path !== '/api/v1/auth/me') {
    // Token might be expired or invalid
    try {
      if (oidc.getSessionGeneration() !== initiatingGeneration) throw new Error('Unauthorized')

      // Try to refresh token
      const refreshed = await oidc.refreshToken()
      if (!refreshed) {
        throw new Error('Refresh discarded or failed')
      }

      // Update store
      if (oidc.token.value) {
        authStore.setToken(oidc.token.value, oidc.user.value)
      } else {
        // Refresh failed, logout
        authStore.clearAuth()
        router.push('/login')
        throw new Error('Unauthorized')
      }

      // Retry request with new token
      const newToken = authStore.getToken()
      if (newToken) {
        headers['Authorization'] = `Bearer ${newToken}`
      }

      res = await fetch(path, {
        ...options,
        headers,
      })
    } catch {
      throw new Error('Unauthorized - please log in again')
    }
  }

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    
    // Handle CSRF validation failure
    if (res.status === 403 && text.includes('CSRF validation failed')) {
      // Token might be expired, reload page to get new token
      window.location.reload()
      throw new Error('CSRF validation failed - page reloaded')
    }
    
    throw new Error(`${res.status} ${res.statusText}${text ? ': ' + text : ''}`)
  }

  if (res.status === 204 || res.headers.get('content-length') === '0') {
    return undefined as T
  }

  return res.json() as Promise<T>
}
