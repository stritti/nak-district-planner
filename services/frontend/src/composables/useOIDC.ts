/**
 * useOIDC - OIDC/OAuth2 PKCE Flow Composable
 * 
 * Handles complete OAuth2 PKCE flow for SPA authentication:
 * - OIDC Discovery
 * - PKCE code challenge generation
 * - Authorization URL generation
 * - Token exchange
 * - Token refresh (with 5min auto-refresh)
 * - Logout
 */

import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

// Types
export interface OIDCToken {
  accessToken: string
  idToken: string
  refreshToken?: string
  expiresAt: number // Unix timestamp in seconds
}

export interface OIDCUser {
  sub: string
  email?: string
  name?: string
  picture?: string
}

export interface OIDCDiscovery {
  authorization_endpoint: string
  token_endpoint: string
  userinfo_endpoint: string
  revocation_endpoint?: string
  jwks_uri?: string
}

// PKCE Helpers
function generateCodeVerifier(): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~'
  const length = 128
  let result = ''
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}

async function generateCodeChallenge(verifier: string): Promise<string> {
  const encoder = new TextEncoder()
  const data = encoder.encode(verifier)
  const digest = await crypto.subtle.digest('SHA-256', data)
  const bytes = new Uint8Array(digest)
  let result = ''
  for (let i = 0; i < bytes.byteLength; i++) {
    result += String.fromCharCode(bytes[i])
  }
  return btoa(result)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '')
}

function generateState(): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  let result = ''
  for (let i = 0; i < 32; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}

function parseJwt(token: string): Record<string, unknown> {
  try {
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )
    return JSON.parse(jsonPayload)
  } catch {
    return {}
  }
}

// Composable
const discoveryUrl = import.meta.env.VITE_OIDC_DISCOVERY_URL || ''
const clientId = import.meta.env.VITE_OIDC_CLIENT_ID || ''
const redirectUri = import.meta.env.VITE_OIDC_REDIRECT_URI || ''

export function useOIDC() {
  let router: ReturnType<typeof useRouter> | null = null
  
  // Lazy-initialize router to avoid issues during app startup
  function getRouter(): ReturnType<typeof useRouter> {
    if (!router) {
      router = useRouter()
    }
    return router
  }

  // State
  const token = ref<OIDCToken | null>(null)
  const user = ref<OIDCUser | null>(null)
  const discovery = ref<OIDCDiscovery | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const refreshTimer = ref<NodeJS.Timeout | null>(null)

  // Computed
  const isAuthenticated = computed(() => token.value !== null)
  const isTokenExpired = computed(() => {
    if (!token.value) return true
    return Date.now() / 1000 >= token.value.expiresAt
  })

  // Task 5.2: OIDC Discovery
  async function loadDiscovery(): Promise<void> {
    if (discovery.value) return

    try {
      isLoading.value = true
      error.value = null

      const res = await fetch(discoveryUrl)
      if (!res.ok) throw new Error('Failed to load OIDC discovery')
      discovery.value = await res.json()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Discovery failed'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // Task 5.3: Authorization URL with PKCE
  async function getAuthorizationUrl(): Promise<string> {
    await loadDiscovery()
    if (!discovery.value) throw new Error('Discovery not loaded')

    const codeVerifier = generateCodeVerifier()
    const codeChallenge = await generateCodeChallenge(codeVerifier)
    const state = generateState()

    // Store in sessionStorage (cleared on browser close)
    sessionStorage.setItem('oidc_code_verifier', codeVerifier)
    sessionStorage.setItem('oidc_state', state)

    const params = new URLSearchParams({
      client_id: clientId,
      redirect_uri: redirectUri,
      response_type: 'code',
      scope: 'openid profile email',
      code_challenge: codeChallenge,
      code_challenge_method: 'S256',
      state,
    })

    return `${discovery.value.authorization_endpoint}?${params.toString()}`
  }

  // Task 5.4: Code Exchange for Tokens
  async function exchangeCodeForToken(code: string): Promise<void> {
    await loadDiscovery()
    if (!discovery.value) throw new Error('Discovery not loaded')

    const codeVerifier = sessionStorage.getItem('oidc_code_verifier')
    if (!codeVerifier) throw new Error('Code verifier not found')

    try {
      isLoading.value = true
      error.value = null

      const params = new URLSearchParams({
        client_id: clientId,
        code,
        code_verifier: codeVerifier,
        grant_type: 'authorization_code',
        redirect_uri: redirectUri,
      })

      const res = await fetch(discovery.value.token_endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: params.toString(),
      })

      if (!res.ok) {
        const errorBody = await res.text()
        throw new Error(`Token exchange failed: ${errorBody}`)
      }

      const data = await res.json()
      const payload = parseJwt(data.id_token || data.access_token)

      token.value = {
        accessToken: data.access_token,
        idToken: data.id_token,
        refreshToken: data.refresh_token,
        expiresAt: Math.floor(Date.now() / 1000) + (data.expires_in || 3600),
      }

      user.value = {
        sub: (payload.sub as string) || '',
        email: (payload.email as string) || undefined,
        name: (payload.name as string) || undefined,
        picture: (payload.picture as string) || undefined,
      }

      // Clean up session storage
      sessionStorage.removeItem('oidc_code_verifier')
      sessionStorage.removeItem('oidc_state')

      // Start refresh timer (5min before expiry)
      setupRefreshTimer()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Token exchange failed'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // Task 5.5: Token Refresh Logic
  async function refreshToken(): Promise<void> {
    if (!token.value?.refreshToken) {
      await logout()
      return
    }

    await loadDiscovery()
    if (!discovery.value) throw new Error('Discovery not loaded')

    try {
      const params = new URLSearchParams({
        client_id: clientId,
        grant_type: 'refresh_token',
        refresh_token: token.value.refreshToken,
      })

      const res = await fetch(discovery.value.token_endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: params.toString(),
      })

      if (!res.ok) {
        // Refresh failed - logout user
        await logout()
        return
      }

      const data = await res.json()
      const payload = parseJwt(data.id_token || data.access_token)

      token.value = {
        accessToken: data.access_token,
        idToken: data.id_token,
        refreshToken: data.refresh_token || token.value.refreshToken,
        expiresAt: Math.floor(Date.now() / 1000) + (data.expires_in || 3600),
      }

      if (payload.email) {
        user.value = {
          ...user.value!,
          email: (payload.email as string),
        }
      }
    } catch (err) {
      console.error('Token refresh failed:', err)
      await logout()
    }
  }

  // Setup auto-refresh timer (5min before expiry)
  function setupRefreshTimer(): void {
    if (refreshTimer.value) clearTimeout(refreshTimer.value)

    if (!token.value) return

    // Refresh 5 minutes before expiry
    const refreshAt = (token.value.expiresAt - 300) * 1000
    const now = Date.now()
    const delay = Math.max(refreshAt - now, 0)

    refreshTimer.value = setTimeout(() => {
      refreshToken()
      setupRefreshTimer() // Reschedule
    }, delay)
  }

  // Task 5.6: Logout
  async function logout(): Promise<void> {
    try {
      // Optional: Call revocation endpoint if available
      if (token.value?.accessToken && discovery.value?.revocation_endpoint) {
        const params = new URLSearchParams({
          client_id: clientId,
          token: token.value.accessToken,
        })

        await fetch(discovery.value.revocation_endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: params.toString(),
        }).catch(() => {
          // Ignore revocation errors
        })
      }
    } finally {
      // Always clear local state
      token.value = null
      user.value = null
      if (refreshTimer.value) clearTimeout(refreshTimer.value)
      sessionStorage.removeItem('oidc_code_verifier')
      sessionStorage.removeItem('oidc_state')
      
      // Try to navigate, but don't fail if router isn't ready yet
      try {
        const rt = getRouter()
        await rt.push('/login')
      } catch (err) {
        console.debug('Could not navigate to login (router may not be ready):', err)
      }
    }
  }

  // Task 5.7: Restore token from authStore (called from store)
  function setToken(t: OIDCToken | null, u: OIDCUser | null = null): void {
    token.value = t
    user.value = u
    if (t) setupRefreshTimer()
  }

  return {
    // State
    token: computed(() => token.value),
    user: computed(() => user.value),
    isAuthenticated,
    isTokenExpired,
    isLoading,
    error,

    // Methods
    loadDiscovery,
    getAuthorizationUrl,
    exchangeCodeForToken,
    refreshToken,
    logout,
    setToken,
  }
}
