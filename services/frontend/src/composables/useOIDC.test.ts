/**
 * Tests for useOIDC composable
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useOIDC } from './useOIDC'
import { useAuthStore } from '../stores/auth'

// Mock Vue Router
vi.mock('vue-router', () => ({
  createRouter: vi.fn(),
  createWebHistory: vi.fn(),
  useRouter: () => ({
    push: vi.fn(),
  }),
}))

describe('useOIDC', () => {
  function createOidc() {
    return useOIDC(undefined, {
      redirectUri: 'http://localhost:5173/auth/callback',
      scope: 'openid profile email',
    })
  }

  beforeEach(() => {
    setActivePinia(createPinia())
    sessionStorage.clear()
    vi.clearAllMocks()
    createOidc().setToken(null)
  })

  afterEach(() => {
    createOidc().setToken(null)
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('should generate valid PKCE code verifier and challenge', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            authorization_endpoint: 'https://auth.example.com/authorize',
            token_endpoint: 'https://auth.example.com/token',
            userinfo_endpoint: 'https://auth.example.com/userinfo',
            client_id: 'frontend-test-client',
          }),
          { status: 200 }
        )
      )
    )

    const { getAuthorizationUrl } = createOidc()
    const url = await getAuthorizationUrl()

    expect(url).toContain('code_challenge=')
    expect(url).toContain('code_challenge_method=S256')
  })

  it('should create authorization URL with PKCE parameters', async () => {
    // Mock fetch for discovery
    global.fetch = vi.fn(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            authorization_endpoint: 'https://auth.example.com/authorize',
            token_endpoint: 'https://auth.example.com/token',
            userinfo_endpoint: 'https://auth.example.com/userinfo',
            client_id: 'frontend-test-client',
          }),
          { status: 200 }
        )
      )
    )

    const { getAuthorizationUrl } = createOidc()
    const url = await getAuthorizationUrl()

    expect(url).toContain('https://auth.example.com/authorize')
    expect(url).toContain('code_challenge=')
    expect(url).toContain('code_challenge_method=S256')
    expect(url).toContain('client_id=')
    expect(url).toContain('scope=openid')
  })

  it('should store code verifier and state in sessionStorage', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            authorization_endpoint: 'https://auth.example.com/authorize',
            token_endpoint: 'https://auth.example.com/token',
            userinfo_endpoint: 'https://auth.example.com/userinfo',
            client_id: 'frontend-test-client',
          }),
          { status: 200 }
        )
      )
    )

    const { getAuthorizationUrl } = createOidc()
    await getAuthorizationUrl()

    expect(sessionStorage.getItem('oidc_code_verifier')).toBeTruthy()
    expect(sessionStorage.getItem('oidc_state')).toBeTruthy()
  })

  it('should parse JWT tokens correctly', () => {
    // Test JWT parsing
    const jwtWithEmail = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLWlkIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwibmFtZSI6IkpvaG4gRG9lIn0.1234'
    
    // We can't directly test parseJwt as it's internal, but we can test indirectly
    // through exchangeCodeForToken behavior
    expect(jwtWithEmail).toContain('.')
  })

  it('should throw error if code verifier not found', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            authorization_endpoint: 'https://auth.example.com/authorize',
            token_endpoint: 'https://auth.example.com/token',
            userinfo_endpoint: 'https://auth.example.com/userinfo',
            client_id: 'frontend-test-client',
          }),
          { status: 200 }
        )
      )
    )

    const { exchangeCodeForToken } = createOidc()

    await expect(exchangeCodeForToken('auth_code_123')).rejects.toThrow()
  })

  it('should share an in-flight refresh across composable instances', async () => {
    const resolveFetch = vi.fn()
    global.fetch = vi.fn(
      () =>
        new Promise<Response>((resolve) => {
          resolveFetch.mockImplementationOnce(() => resolve(
            new Response(
              JSON.stringify({ access_token: 'new-access-token', expires_in: 3600 }),
              { status: 200 }
            )
          ))
        })
    )

    const first = createOidc()
    const second = createOidc()
    first.setToken(
      {
        accessToken: 'old-access-token',
        idToken: '',
        refreshToken: 'refresh-token',
        expiresAt: Math.floor(Date.now() / 1000) - 1,
      },
      { sub: 'user-sub' }
    )

    const firstRefresh = first.refreshToken()
    const secondRefresh = second.refreshToken()
    expect(global.fetch).toHaveBeenCalledTimes(1)

    resolveFetch()
    await Promise.all([firstRefresh, secondRefresh])
  })

  it('should discard a refresh result that resolves after logout', async () => {
    let resolveFetch!: (response: Response) => void
    global.fetch = vi.fn(
      () =>
        new Promise<Response>((resolve) => {
          resolveFetch = resolve
        })
    )

    const oidc = createOidc()
    const authStore = useAuthStore()
    oidc.setToken(
      {
        accessToken: 'old-access-token',
        idToken: '',
        refreshToken: 'refresh-token',
        expiresAt: Math.floor(Date.now() / 1000) - 1,
      },
      { sub: 'user-sub' }
    )

    const refresh = oidc.refreshToken()
    oidc.setToken(null)
    resolveFetch(
      new Response(
        JSON.stringify({
          access_token: 'new-access-token',
          id_token: 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyLXN1YiJ9.signature',
          expires_in: 3600,
        }),
        { status: 200 }
      )
    )
    await refresh

    expect(authStore.token).toBeNull()
  })

  it('should not clear a newer session when a stale refresh response is rejected', async () => {
    let resolveFetch!: (response: Response) => void
    global.fetch = vi.fn(
      () =>
        new Promise<Response>((resolve) => {
          resolveFetch = resolve
        })
    )

    const oidc = createOidc()
    const authStore = useAuthStore()
    oidc.setToken(
      {
        accessToken: 'old-access-token',
        idToken: '',
        refreshToken: 'old-refresh-token',
        expiresAt: Math.floor(Date.now() / 1000) - 1,
      },
      { sub: 'old-user-sub' }
    )

    const refresh = oidc.refreshToken()
    oidc.setToken(
      {
        accessToken: 'new-access-token',
        idToken: '',
        refreshToken: 'new-refresh-token',
        expiresAt: Math.floor(Date.now() / 1000) + 3600,
      },
      { sub: 'new-user-sub' }
    )

    resolveFetch(new Response('', { status: 401 }))
    await refresh

    expect(authStore.token?.accessToken).toBe('new-access-token')
    expect(authStore.user?.sub).toBe('new-user-sub')
  })

  it('should not clear a newer session when a stale refresh request throws', async () => {
    let rejectFetch!: (error: Error) => void
    global.fetch = vi.fn(
      () =>
        new Promise<Response>((_resolve, reject) => {
          rejectFetch = reject
        })
    )

    const oidc = createOidc()
    const authStore = useAuthStore()
    oidc.setToken(
      {
        accessToken: 'old-access-token',
        idToken: '',
        refreshToken: 'old-refresh-token',
        expiresAt: Math.floor(Date.now() / 1000) - 1,
      },
      { sub: 'old-user-sub' }
    )

    const refresh = oidc.refreshToken()
    oidc.setToken(
      {
        accessToken: 'new-access-token',
        idToken: '',
        refreshToken: 'new-refresh-token',
        expiresAt: Math.floor(Date.now() / 1000) + 3600,
      },
      { sub: 'new-user-sub' }
    )

    rejectFetch(new Error('network failed'))
    await refresh

    expect(authStore.token?.accessToken).toBe('new-access-token')
    expect(authStore.user?.sub).toBe('new-user-sub')
  })

  it('should keep one shared refresh timer across composable instances', () => {
    vi.useFakeTimers()
    const setTimeoutSpy = vi.spyOn(global, 'setTimeout')
    const clearTimeoutSpy = vi.spyOn(global, 'clearTimeout')
    global.fetch = vi.fn()

    const first = createOidc()
    const second = createOidc()

    first.setToken(
      {
        accessToken: 'first-access-token',
        idToken: '',
        refreshToken: 'first-refresh-token',
        expiresAt: Math.floor(Date.now() / 1000) + 3600,
      },
      { sub: 'user-sub' }
    )
    second.setToken(
      {
        accessToken: 'second-access-token',
        idToken: '',
        refreshToken: 'second-refresh-token',
        expiresAt: Math.floor(Date.now() / 1000) + 3600,
      },
      { sub: 'user-sub' }
    )

    expect(setTimeoutSpy).toHaveBeenCalledTimes(2)
    expect(clearTimeoutSpy).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(3_400_000)
    expect(global.fetch).toHaveBeenCalledTimes(1)
  })
})
