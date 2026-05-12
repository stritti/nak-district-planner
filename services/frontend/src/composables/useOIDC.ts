import { computed, ref } from 'vue'
import { useRouter, type Router } from 'vue-router'
import { useAuthStore } from '../stores/auth'

export interface OIDCToken {
  accessToken: string
  idToken: string
  refreshToken?: string
  expiresAt: number
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
  userinfo_endpoint?: string
  revocation_endpoint?: string
  end_session_endpoint?: string
  jwks_uri?: string
}

export interface OIDCConfig {
  discoveryUrl: string
  clientId: string
  redirectUri: string
  scope: string
}

const SESSION_CODE_VERIFIER_KEY = 'oidc_code_verifier'
const SESSION_STATE_KEY = 'oidc_state'

const envConfig: OIDCConfig = {
  discoveryUrl: import.meta.env.VITE_OIDC_DISCOVERY_URL || '',
  clientId: import.meta.env.VITE_OIDC_CLIENT_ID || '',
  redirectUri: import.meta.env.VITE_OIDC_REDIRECT_URI || '',
  scope: import.meta.env.VITE_OIDC_SCOPE || 'openid profile email',
}

function toBase64Url(bytes: Uint8Array): string {
  const binary = Array.from(bytes, (byte) => String.fromCharCode(byte)).join('')
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '')
}

function generateCodeVerifier(): string {
  const bytes = new Uint8Array(96)
  crypto.getRandomValues(bytes)
  return toBase64Url(bytes)
}

async function generateCodeChallenge(verifier: string): Promise<string> {
  const data = new TextEncoder().encode(verifier)
  const digest = await crypto.subtle.digest('SHA-256', data)
  return toBase64Url(new Uint8Array(digest))
}

function generateState(): string {
  const bytes = new Uint8Array(32)
  crypto.getRandomValues(bytes)
  return toBase64Url(bytes)
}

function parseJwt(token: string): Record<string, unknown> {
  try {
    const base64Url = token.split('.')[1]
    if (!base64Url) return {}
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const padding = '='.repeat((4 - (base64.length % 4)) % 4)
    return JSON.parse(atob(base64 + padding)) as Record<string, unknown>
  } catch {
    return {}
  }
}

export function useOIDC(router?: Router, config?: Partial<OIDCConfig>) {
  let injectedRouter: Router | null = router || null
  const authStore = useAuthStore()
  const oidcConfig: OIDCConfig = { ...envConfig, ...(config || {}) }

  const discovery = ref<OIDCDiscovery | null>(null)
  const discoveryPromise = ref<Promise<void> | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const refreshTimer = ref<ReturnType<typeof setTimeout> | null>(null)
  const refreshInFlight = ref<Promise<void> | null>(null)

  const token = computed(() => authStore.token)
  const user = computed(() => authStore.user)
  const isAuthenticated = computed(() => authStore.isAuthenticated)
  const isTokenExpired = computed(() => {
    if (!authStore.token) return true
    return Date.now() / 1000 >= authStore.token.expiresAt
  })

  function getRouter(): Router {
    if (!injectedRouter) injectedRouter = useRouter()
    return injectedRouter
  }

  function assertConfig(): void {
    if (!oidcConfig.discoveryUrl) throw new Error('OIDC discovery URL is not configured')
    if (!oidcConfig.clientId) throw new Error('OIDC client ID is not configured')
    if (!oidcConfig.redirectUri) throw new Error('OIDC redirect URI is not configured')
  }

  function clearLocalArtifacts(): void {
    sessionStorage.removeItem(SESSION_CODE_VERIFIER_KEY)
    sessionStorage.removeItem(SESSION_STATE_KEY)
  }

  async function fetchUserInfo(accessToken: string): Promise<OIDCUser | null> {
    const endpoint = discovery.value?.userinfo_endpoint
    if (!endpoint) return null

    const response = await fetch(endpoint, {
      headers: { Authorization: `Bearer ${accessToken}` },
    })

    if (!response.ok) return null

    const data = await response.json()
    if (!data.sub) return null

    return {
      sub: data.sub,
      email: data.email,
      name: data.name,
      picture: data.picture,
    }
  }

  async function loadDiscovery(): Promise<void> {
    if (discovery.value) return
    if (discoveryPromise.value) return discoveryPromise.value

    assertConfig()

    const promise = (async () => {
      isLoading.value = true
      error.value = null

      try {
        const response = await fetch(oidcConfig.discoveryUrl)
        if (!response.ok) {
          throw new Error(`Failed to load OIDC discovery (${response.status})`)
        }

        const data = (await response.json()) as OIDCDiscovery
        if (!data.authorization_endpoint || !data.token_endpoint) {
          throw new Error('OIDC discovery document misses required endpoints')
        }

        discovery.value = data
      } catch (err) {
        error.value = err instanceof Error ? err.message : 'Discovery failed'
        throw err
      } finally {
        isLoading.value = false
      }
    })()

    discoveryPromise.value = promise
    try {
      await promise
    } finally {
      discoveryPromise.value = null
    }
  }

  async function getAuthorizationUrl(): Promise<string> {
    await loadDiscovery()
    if (!discovery.value) throw new Error('Discovery not loaded')

    const codeVerifier = generateCodeVerifier()
    const codeChallenge = await generateCodeChallenge(codeVerifier)
    const state = generateState()

    sessionStorage.setItem(SESSION_CODE_VERIFIER_KEY, codeVerifier)
    sessionStorage.setItem(SESSION_STATE_KEY, state)

    const params = new URLSearchParams({
      client_id: oidcConfig.clientId,
      redirect_uri: oidcConfig.redirectUri,
      response_type: 'code',
      scope: oidcConfig.scope,
      code_challenge: codeChallenge,
      code_challenge_method: 'S256',
      state,
    })

    return `${discovery.value.authorization_endpoint}?${params.toString()}`
  }

  async function exchangeCodeForToken(code: string): Promise<void> {
    await loadDiscovery()
    if (!discovery.value) throw new Error('Discovery not loaded')

    const codeVerifier = sessionStorage.getItem(SESSION_CODE_VERIFIER_KEY)
    if (!codeVerifier) throw new Error('Code verifier not found in session storage')

    isLoading.value = true
    error.value = null

    try {
      const body = new URLSearchParams({
        grant_type: 'authorization_code',
        client_id: oidcConfig.clientId,
        code,
        redirect_uri: oidcConfig.redirectUri,
        code_verifier: codeVerifier,
      })

      const response = await fetch(discovery.value.token_endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: body.toString(),
      })

      if (!response.ok) {
        const raw = await response.text()
        let parsed: unknown = raw
        try {
          parsed = JSON.parse(raw)
        } catch {
          // keep raw text
        }
        throw new Error(`Token exchange failed (${response.status}): ${JSON.stringify(parsed)}`)
      }

      const data = await response.json()
      if (!data.access_token) throw new Error('Token response missing access_token')

      const claims = parseJwt((data.id_token as string) || (data.access_token as string))
      const nextToken: OIDCToken = {
        accessToken: data.access_token,
        idToken: data.id_token || '',
        refreshToken: data.refresh_token,
        expiresAt: Math.floor(Date.now() / 1000) + Number(data.expires_in || 3600),
      }

      let nextUser: OIDCUser | null = {
        sub: (claims.sub as string) || '',
        email: (claims.email as string) || undefined,
        name: (claims.name as string) || undefined,
        picture: (claims.picture as string) || undefined,
      }

      if (!nextUser.sub) {
        nextUser = await fetchUserInfo(nextToken.accessToken)
      }

      if (!nextUser?.sub) {
        throw new Error('OIDC identity missing: no sub in id_token/access_token or userinfo response')
      }

      authStore.setToken(nextToken, nextUser)
      clearLocalArtifacts()
      setupRefreshTimer()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Token exchange failed'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function refreshToken(): Promise<void> {
    if (refreshInFlight.value) return refreshInFlight.value

    const operation = (async () => {
      const current = authStore.token
      if (!current?.refreshToken) {
        await logout()
        return
      }

      await loadDiscovery()
      if (!discovery.value) throw new Error('Discovery not loaded')

      try {
        const body = new URLSearchParams({
          grant_type: 'refresh_token',
          client_id: oidcConfig.clientId,
          refresh_token: current.refreshToken,
        })

        const response = await fetch(discovery.value.token_endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: body.toString(),
        })

        if (!response.ok) {
          await logout()
          return
        }

        const data = await response.json()
        if (!data.access_token) {
          await logout()
          return
        }

        const claims = parseJwt((data.id_token as string) || (data.access_token as string))
        let nextUser: OIDCUser | null = authStore.user

        if (claims.sub) {
          nextUser = {
            sub: claims.sub as string,
            email: (claims.email as string) || authStore.user?.email,
            name: (claims.name as string) || authStore.user?.name,
            picture: (claims.picture as string) || authStore.user?.picture,
          }
        } else if (!authStore.user?.sub) {
          nextUser = await fetchUserInfo(data.access_token)
        }

        if (!nextUser?.sub) {
          await logout()
          return
        }

        const nextToken: OIDCToken = {
          accessToken: data.access_token,
          idToken: data.id_token || current.idToken,
          refreshToken: data.refresh_token || current.refreshToken,
          expiresAt: Math.floor(Date.now() / 1000) + Number(data.expires_in || 3600),
        }

        authStore.setToken(nextToken, nextUser)
        setupRefreshTimer()
      } catch (err) {
        console.error('OIDC refresh failed', err)
        await logout()
      }
    })()

    refreshInFlight.value = operation
    try {
      await operation
    } finally {
      refreshInFlight.value = null
    }
  }

  function setupRefreshTimer(): void {
    if (refreshTimer.value) clearTimeout(refreshTimer.value)
    if (!authStore.token) return

    const nowSeconds = Date.now() / 1000
    const ttlSeconds = Math.max(authStore.token.expiresAt - nowSeconds, 0)

    // Avoid refresh loops for short-lived tokens.
    // Refresh at ~80% of lifetime with sane bounds.
    const refreshLeadSeconds = Math.min(300, Math.max(5, Math.floor(ttlSeconds * 0.2)))
    const delay = Math.max((ttlSeconds - refreshLeadSeconds) * 1000, 1000)

    refreshTimer.value = setTimeout(() => {
      void refreshToken()
    }, delay)
  }

  async function logout(): Promise<void> {
    const current = authStore.token

    try {
      await loadDiscovery().catch(() => {
        // best effort
      })

      const revocationEndpoint = discovery.value?.revocation_endpoint
      if (current && revocationEndpoint) {
        const body = new URLSearchParams({
          client_id: oidcConfig.clientId,
          token: current.refreshToken || current.accessToken,
        })

        await fetch(revocationEndpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: body.toString(),
        }).catch(() => {
          // ignore remote logout errors
        })
      }
    } finally {
      if (refreshTimer.value) clearTimeout(refreshTimer.value)
      clearLocalArtifacts()
      authStore.clearAuth()

      try {
        await getRouter().push('/login')
      } catch {
        // router can be unavailable during startup/tests
      }
    }
  }

  function setToken(nextToken: OIDCToken | null, nextUser: OIDCUser | null = null): void {
    authStore.setToken(nextToken, nextUser)
    if (nextToken) setupRefreshTimer()
  }

  function initialize(): void {
    if (!authStore.token) return

    if (Date.now() / 1000 >= authStore.token.expiresAt) {
      void refreshToken()
      return
    }

    setupRefreshTimer()
  }

  return {
    token,
    user,
    isAuthenticated,
    isTokenExpired,
    isLoading,
    error,
    loadDiscovery,
    getAuthorizationUrl,
    exchangeCodeForToken,
    refreshToken,
    logout,
    setToken,
    initialize,
  }
}
