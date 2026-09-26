import { useAuthStore } from '../stores/auth'
import { useOIDC } from '../composables/useOIDC'
import { useCSRF } from '../composables/useCSRF'
import { router } from '../router'
import { UnauthorizedError } from './errors'

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const authStore = useAuthStore()
  const { getCSRFHeaders } = useCSRF()
  const oidc = useOIDC(router)

  // If the access token already expired (e.g. the scheduled refresh timer
  // was throttled while the tab was backgrounded), refresh it up front
  // instead of firing an unauthenticated request that is bound to 401.
  if (authStore.token && authStore.isTokenExpired) {
    const preflightGeneration = oidc.getSessionGeneration()
    const refreshed = await oidc.refreshToken()
    if (!refreshed || oidc.getSessionGeneration() !== preflightGeneration) {
      throw new UnauthorizedError()
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
    try {
      res = await retryAfterUnauthorized(res, path, options, headers, {
        getGeneration: () => oidc.getSessionGeneration(),
        initiatingGeneration,
        initialToken: token,
        getToken: () => authStore.getToken(),
        refreshToken: () => oidc.refreshToken(),
        onTokenDropped: () => {
          authStore.clearAuth()
          router.push('/login')
        },
      })
    } catch (err) {
      throw new UnauthorizedError(err)
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

interface UnauthorizedRetryContext {
  getGeneration: () => number
  initiatingGeneration: number
  initialToken: string | null
  getToken: () => string | null
  refreshToken: () => Promise<boolean>
  onTokenDropped: () => void
}

async function retryAfterUnauthorized(
  initialResponse: Response,
  path: string,
  options: RequestInit,
  headers: Record<string, string>,
  context: UnauthorizedRetryContext,
): Promise<Response> {
  const { getGeneration, initiatingGeneration, initialToken } = context

  // The initiating request must never execute under a replacement identity.
  const assertSessionUnchanged = (): void => {
    if (getGeneration() !== initiatingGeneration) throw new Error('Session replaced')
  }

  assertSessionUnchanged()

  let res = initialResponse

  // Another tab may already have replaced the bearer used by the first
  // request. Retry once before triggering another token rotation.
  const alreadyRotated = context.getToken()
  if (alreadyRotated && alreadyRotated !== initialToken) {
    headers['Authorization'] = `Bearer ${alreadyRotated}`
    assertSessionUnchanged()
    res = await fetch(path, { ...options, headers })
    assertSessionUnchanged()
  }

  if (res.status !== 401) return res

  const refreshed = await context.refreshToken()
  if (!refreshed) throw new Error('Refresh discarded')
  assertSessionUnchanged()

  // Retry request with new token
  const newToken = context.getToken()
  if (newToken) {
    headers['Authorization'] = `Bearer ${newToken}`
  } else {
    context.onTokenDropped()
    throw new Error('No token after refresh')
  }

  return await fetch(path, { ...options, headers })
}
