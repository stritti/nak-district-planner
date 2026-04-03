import { useAuthStore } from '@/stores/auth'

// Task 8.1: Create fetch wrapper with JWT interceptor
export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const authStore = useAuthStore()
  
  // Task 8.2: Add Authorization header
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  const token = authStore.getToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  let res = await fetch(path, {
    ...options,
    headers,
  })

  // Task 8.3: Handle 401 and refresh token
  if (res.status === 401) {
    // Token might be expired or invalid
    try {
      const { useOIDC } = await import('@/composables/useOIDC')
      const { useRouter } = await import('vue-router')
      
      // Get router instance (may be undefined if called outside component context)
      let routerInstance
      try {
        routerInstance = useRouter()
      } catch {
        // Router not available in this context, that's ok
      }
      
      const oidc = useOIDC(routerInstance)

      // Try to refresh token
      await oidc.refreshToken()

      // Update store
      if (oidc.token.value) {
        authStore.setToken(oidc.token.value, oidc.user.value)
      } else {
        // Refresh failed, logout
        authStore.clearAuth()
        const { router } = await import('@/router')
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
      authStore.clearAuth()
      throw new Error('Unauthorized - please log in again')
    }
  }

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`${res.status} ${res.statusText}${text ? ': ' + text : ''}`)
  }

  if (res.status === 204 || res.headers.get('content-length') === '0') {
    return undefined as T
  }

  return res.json() as Promise<T>
}
