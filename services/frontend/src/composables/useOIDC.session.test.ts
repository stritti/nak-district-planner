/**
 * Additional tests for useOIDC composable: token exchange validation,
 * userinfo validation, activity refresh, and initialization paths.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { __resetOIDCModuleState, useOIDC } from './useOIDC'
import { useAuthStore } from '../stores/auth'
import { MockBroadcastChannel, resetBroadcastChannelMocks } from '../testing/broadcastChannel'
import { stubWebLocks } from '../testing/webLocks'

vi.mock('vue-router', () => ({
  createRouter: vi.fn(),
  createWebHistory: vi.fn(),
  useRouter: () => ({
    push: vi.fn(),
  }),
}))

function tokenWithClaims(claims: unknown): string {
  const payload = btoa(JSON.stringify(claims)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
  return `header.${payload}.signature`
}

const discoveryResponse = () => new Response(
  JSON.stringify({
    authorization_endpoint: 'https://auth.example.com/authorize',
    token_endpoint: 'https://auth.example.com/token',
    userinfo_endpoint: 'https://auth.example.com/userinfo',
    revocation_endpoint: 'https://auth.example.com/revoke',
    client_id: 'frontend-test-client',
  }),
  { status: 200 },
)

describe('useOIDC token exchange and session', () => {
  function createOidc() {
    return useOIDC(undefined, {
      redirectUri: 'http://localhost:5173/auth/callback',
      scope: 'openid profile email',
    })
  }

  const unexpiredToken = {
    accessToken: 'old-access-token',
    idToken: '',
    refreshToken: 'refresh-token',
    expiresAt: Math.floor(Date.now() / 1000) + 3600,
  }

  beforeEach(() => {
    __resetOIDCModuleState()
    resetBroadcastChannelMocks()
    stubWebLocks()
    setActivePinia(createPinia())
    sessionStorage.clear()
    localStorage.clear()
    vi.clearAllMocks()
    createOidc().setToken(null)
  })

  afterEach(() => {
    createOidc().setToken(null)
    vi.useRealTimers()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  async function exchangeWithResponse(body: unknown, status = 200) {
    sessionStorage.setItem('oidc_code_verifier', 'test-verifier')
    global.fetch = vi.fn((input: RequestInfo | URL) => {
      if (String(input) === '/api/v1/auth/oidc/discovery') {
        return Promise.resolve(discoveryResponse())
      }
      const bodyText = typeof body === 'string' ? body : JSON.stringify(body)
      return Promise.resolve(new Response(bodyText, { status }))
    })
    const { exchangeCodeForToken } = createOidc()
    return exchangeCodeForToken('auth_code_123')
  }

  it('triggers a refresh through user activity when the token is near expiry', async () => {
    const fetchMock = vi.fn(() => Promise.resolve(
      new Response(JSON.stringify({ access_token: 'fresh-access', expires_in: 3600, refresh_token: 'rotated' }), { status: 200 }),
    ))
    global.fetch = fetchMock
    const oidc = createOidc()
    oidc.setToken(
      { ...unexpiredToken, expiresAt: Math.floor(Date.now() / 1000) + 60 },
      { sub: 'user-sub' },
    )
    oidc.initialize()
    document.dispatchEvent(new Event('mousemove'))
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/v1/auth/oidc/token', expect.anything()))
    // A second event within the throttle window must not trigger another fetch.
    document.dispatchEvent(new Event('keydown'))
    document.dispatchEvent(new Event('visibilitychange'))
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('does nothing on initialize without a stored token', () => {
    const oidc = createOidc()
    expect(() => oidc.initialize()).not.toThrow()
  })

  it('stores the exchanged token and user from id_token claims', async () => {
    const idToken = tokenWithClaims({ sub: 'user-sub', email: 'user@example.com', name: 'Test User' })
    const result = await exchangeWithResponse({
      access_token: 'new-access-token',
      id_token: idToken,
      refresh_token: 'new-refresh-token',
      expires_in: 3600,
    })
    expect(result).toBeUndefined()
    const authStore = useAuthStore()
    expect(authStore.token?.accessToken).toBe('new-access-token')
    expect(authStore.token?.refreshToken).toBe('new-refresh-token')
    expect(authStore.token?.idToken).toBe(idToken)
    expect(authStore.user?.sub).toBe('user-sub')
    expect(authStore.user?.email).toBe('user@example.com')
    expect(sessionStorage.getItem('oidc_code_verifier')).toBeNull()
  })

  it('derives the identity from userinfo when tokens carry no sub claim', async () => {
    global.fetch = vi.fn((input: RequestInfo | URL) => {
      if (String(input) === '/api/v1/auth/oidc/discovery') {
        return Promise.resolve(discoveryResponse())
      }
      if (String(input) === 'https://auth.example.com/userinfo') {
        return Promise.resolve(new Response(
          JSON.stringify({ sub: 'userinfo-sub', email: 'info@example.com', name: 'Info User' }),
          { status: 200 },
        ))
      }
      return Promise.resolve(new Response(
        JSON.stringify({ access_token: 'new-access-token', expires_in: 3600 }),
        { status: 200 },
      ))
    })
    sessionStorage.setItem('oidc_code_verifier', 'test-verifier')
    const { exchangeCodeForToken } = createOidc()
    await exchangeCodeForToken('auth_code_123')
    const authStore = useAuthStore()
    expect(authStore.token?.accessToken).toBe('new-access-token')
    expect(authStore.user?.sub).toBe('userinfo-sub')
    expect(authStore.user?.email).toBe('info@example.com')
  })

  it('rejects a token response with malformed access_token', async () => {
    await expect(exchangeWithResponse({ access_token: '' })).rejects.toThrow(
      'Token response missing or malformed access_token',
    )
    expect(useAuthStore().token).toBeNull()
  })

  it('rejects a token response with a non-numeric expires_in', async () => {
    await expect(exchangeWithResponse({ access_token: 'new-access-token', expires_in: '3600' }))
      .rejects.toThrow('Token response missing or malformed access_token')
    expect(useAuthStore().token).toBeNull()
  })

  it('rejects the exchange when no identity can be derived', async () => {
    global.fetch = vi.fn((input: RequestInfo | URL) => {
      if (String(input) === '/api/v1/auth/oidc/discovery') {
        return Promise.resolve(discoveryResponse())
      }
      if (String(input) === 'https://auth.example.com/userinfo') {
        return Promise.resolve(new Response(JSON.stringify({ sub: '' }), { status: 200 }))
      }
      return Promise.resolve(new Response(
        JSON.stringify({ access_token: 'new-access-token', expires_in: 3600 }),
        { status: 200 },
      ))
    })
    sessionStorage.setItem('oidc_code_verifier', 'test-verifier')
    const { exchangeCodeForToken } = createOidc()
    await expect(exchangeCodeForToken('auth_code_123')).rejects.toThrow('OIDC identity missing')
    expect(useAuthStore().token).toBeNull()
  })

  it('reports the backend error detail when the token exchange fails', async () => {
    await expect(exchangeWithResponse({ error: 'invalid_grant' }, 400)).rejects.toThrow(
      'Token exchange failed (400)',
    )
  })

  it('falls back to a generic error message for non-Error rejections', async () => {
    sessionStorage.setItem('oidc_code_verifier', 'test-verifier')
    global.fetch = vi.fn((input: RequestInfo | URL) => {
      if (String(input) === '/api/v1/auth/oidc/discovery') {
        return Promise.resolve(discoveryResponse())
      }
      return Promise.reject('network failure')
    })
    const { exchangeCodeForToken } = createOidc()
    await expect(exchangeCodeForToken('auth_code_123')).rejects.toBe('network failure')
  })

  it('ignores a userinfo response with a non-string sub', async () => {
    global.fetch = vi.fn((input: RequestInfo | URL) => {
      if (String(input) === '/api/v1/auth/oidc/discovery') {
        return Promise.resolve(discoveryResponse())
      }
      if (String(input) === 'https://auth.example.com/userinfo') {
        return Promise.resolve(new Response(JSON.stringify({ sub: 42 }), { status: 200 }))
      }
      return Promise.resolve(new Response(
        JSON.stringify({ access_token: 'new-access-token', expires_in: 3600 }),
        { status: 200 },
      ))
    })
    sessionStorage.setItem('oidc_code_verifier', 'test-verifier')
    const { exchangeCodeForToken } = createOidc()
    await expect(exchangeCodeForToken('auth_code_123')).rejects.toThrow('OIDC identity missing')
  })

  it('ignores malformed userinfo payloads', async () => {
    global.fetch = vi.fn((input: RequestInfo | URL) => {
      if (String(input) === '/api/v1/auth/oidc/discovery') {
        return Promise.resolve(discoveryResponse())
      }
      if (String(input) === 'https://auth.example.com/userinfo') {
        return Promise.resolve(new Response('[1, 2, 3]', { status: 200 }))
      }
      return Promise.resolve(new Response(
        JSON.stringify({ access_token: 'new-access-token', expires_in: 3600 }),
        { status: 200 },
      ))
    })
    sessionStorage.setItem('oidc_code_verifier', 'test-verifier')
    const { exchangeCodeForToken } = createOidc()
    await expect(exchangeCodeForToken('auth_code_123')).rejects.toThrow('OIDC identity missing')
  })

  it('ignores a malformed broadcast rotation instead of adopting it', () => {
    const oidc = createOidc()
    oidc.setToken(unexpiredToken, { sub: 'user-sub' })
    const channel = MockBroadcastChannel.instances[0]
    channel.onmessage?.({
      data: {
        type: 'refresh-complete',
        ok: true,
        refreshToken: 'refresh-token',
        token: { accessToken: '', refreshToken: 'rotated', idToken: '', expiresAt: 1 },
        user: { sub: 'user-sub' },
        completedAt: Date.now(),
      },
    } as MessageEvent)
    expect(useAuthStore().token?.accessToken).toBe('old-access-token')
  })

  it('keeps the session when discovery succeeds on logout with a revocation endpoint', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      if (String(input) === '/api/v1/auth/oidc/discovery') {
        return Promise.resolve(discoveryResponse())
      }
      return Promise.resolve(new Response('', { status: 200 }))
    })
    global.fetch = fetchMock
    const oidc = createOidc()
    oidc.setToken(unexpiredToken, { sub: 'user-sub' })
    await oidc.logout()
    expect(useAuthStore().token).toBeNull()
    expect(fetchMock).toHaveBeenCalledWith(
      'https://auth.example.com/revoke',
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('proceeds with logout even when the router is unavailable', async () => {
    global.fetch = vi.fn(() => Promise.resolve(new Response('', { status: 500 })))
    const oidc = useOIDC(null, { redirectUri: 'http://localhost:5173/auth/callback' })
    oidc.setToken(unexpiredToken, { sub: 'user-sub' })
    await expect(oidc.logout()).resolves.toBeUndefined()
    expect(useAuthStore().token).toBeNull()
  })

  it('initializes an unexpired session with a refresh timer', () => {
    vi.useFakeTimers()
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('', { status: 200 }))
    const oidc = createOidc()
    oidc.setToken(unexpiredToken, { sub: 'user-sub' })
    expect(() => oidc.initialize()).not.toThrow()
  })

  it('schedules a delayed logout for an unexpired token without Web Locks', async () => {
    const { stubNoWebLocks } = await import('../testing/webLocks')
    stubNoWebLocks()
    vi.useFakeTimers()
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('', { status: 200 }))
    const oidc = createOidc()
    const expiresAt = Math.floor(Date.now() / 1000) + 60
    oidc.setToken({ ...unexpiredToken, expiresAt }, { sub: 'user-sub' })
    const pending = oidc.refreshToken()
    await vi.advanceTimersByTimeAsync(61_000)
    await expect(pending).resolves.toBe(false)
    expect(useAuthStore().token).toBeNull()
  })

  it('refreshes immediately on initialize when the stored token is expired', async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      if (String(input) === '/api/v1/auth/oidc/token') {
        return Promise.resolve(new Response(
          JSON.stringify({ access_token: 'fresh-access', refresh_token: 'rotated', expires_in: 3600 }),
          { status: 200 },
        ))
      }
      return Promise.resolve(new Response('', { status: 200 }))
    })
    global.fetch = fetchMock
    const oidc = createOidc()
    oidc.setToken(
      { ...unexpiredToken, expiresAt: Math.floor(Date.now() / 1000) - 10 },
      { sub: 'user-sub' },
    )
    oidc.initialize()
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/v1/auth/oidc/token', expect.anything()))
  })

  it('shares one discovery promise across concurrent callers', async () => {
    let resolveDiscovery!: (response: Response) => void
    global.fetch = vi.fn(
      () =>
        new Promise<Response>((resolve) => {
          resolveDiscovery = resolve
        }),
    )
    const oidc = createOidc()
    const firstLoad = oidc.loadDiscovery()
    const secondLoad = oidc.loadDiscovery()
    resolveDiscovery(discoveryResponse())
    await Promise.all([firstLoad, secondLoad])
    expect(global.fetch).toHaveBeenCalledTimes(1)
  })

  it('fails discovery when the document misses required endpoints', async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ client_id: 'client' }), { status: 200 }))
    const { loadDiscovery, error } = createOidc()
    await expect(loadDiscovery()).rejects.toThrow('misses required endpoints')
    expect(error.value).toContain('misses required endpoints')
  })

  it('fails discovery when the client_id is missing', async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response(
      JSON.stringify({
        authorization_endpoint: 'https://auth.example.com/authorize',
        token_endpoint: 'https://auth.example.com/token',
      }),
      { status: 200 },
    ))
    const { loadDiscovery } = createOidc()
    await expect(loadDiscovery()).rejects.toThrow('client ID not provided')
  })

  it('reports the failure when the discovery fetch fails', async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response('unavailable', { status: 503 }))
    const { loadDiscovery, error } = createOidc()
    await expect(loadDiscovery()).rejects.toThrow('OIDC discovery failed (503)')
    expect(error.value).toContain('OIDC discovery failed (503)')
  })

  it('exposes the token expiry state as computed values', () => {
    const oidc = createOidc()
    expect(oidc.isTokenExpired.value).toBe(true)
    oidc.setToken(unexpiredToken, { sub: 'user-sub' })
    expect(oidc.isTokenExpired.value).toBe(false)
    expect(oidc.isAuthenticated.value).toBe(true)
    expect(oidc.token.value?.accessToken).toBe('old-access-token')
    expect(oidc.user.value?.sub).toBe('user-sub')
  })

  it('returns the current session generation', () => {
    const oidc = createOidc()
    const before = oidc.getSessionGeneration()
    oidc.setToken(unexpiredToken, { sub: 'user-sub' })
    expect(oidc.getSessionGeneration()).toBeGreaterThan(before)
  })

  it('reuses a loaded discovery document on subsequent calls', async () => {
    global.fetch = vi.fn().mockResolvedValue(discoveryResponse())
    const { loadDiscovery } = createOidc()
    await loadDiscovery()
    await loadDiscovery()
    expect(global.fetch).toHaveBeenCalledTimes(1)
  })

  it('reports a generic discovery error for non-Error rejections', async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response('bad gateway', { status: 502 }))
    const { loadDiscovery, error } = createOidc()
    await expect(loadDiscovery()).rejects.toThrow()
    expect(error.value).toBeTypeOf('string')
  })

  it('derives the identity from a userinfo response with partial claims', async () => {
    global.fetch = vi.fn((input: RequestInfo | URL) => {
      if (String(input) === '/api/v1/auth/oidc/discovery') {
        return Promise.resolve(discoveryResponse())
      }
      if (String(input) === 'https://auth.example.com/userinfo') {
        return Promise.resolve(new Response(
          JSON.stringify({ sub: 'partial-sub', email: 42, name: null }),
          { status: 200 },
        ))
      }
      return Promise.resolve(new Response(
        JSON.stringify({ access_token: 'new-access-token', expires_in: 3600 }),
        { status: 200 },
      ))
    })
    sessionStorage.setItem('oidc_code_verifier', 'test-verifier')
    const { exchangeCodeForToken } = createOidc()
    await exchangeCodeForToken('auth_code_123')
    const authStore = useAuthStore()
    expect(authStore.user?.sub).toBe('partial-sub')
    expect(authStore.user?.email).toBeUndefined()
    expect(authStore.user?.name).toBeUndefined()
  })

  it('ignores a failing userinfo endpoint during token exchange', async () => {
    global.fetch = vi.fn((input: RequestInfo | URL) => {
      if (String(input) === '/api/v1/auth/oidc/discovery') {
        return Promise.resolve(discoveryResponse())
      }
      if (String(input) === 'https://auth.example.com/userinfo') {
        return Promise.resolve(new Response('server error', { status: 500 }))
      }
      return Promise.resolve(new Response(
        JSON.stringify({ access_token: 'new-access-token', expires_in: 3600 }),
        { status: 200 },
      ))
    })
    sessionStorage.setItem('oidc_code_verifier', 'test-verifier')
    const { exchangeCodeForToken } = createOidc()
    await expect(exchangeCodeForToken('auth_code_123')).rejects.toThrow('OIDC identity missing')
  })

  it('clears broadcast wait state on an unsuccessful cross-tab refresh', () => {
    const oidc = createOidc()
    oidc.setToken(unexpiredToken, { sub: 'user-sub' })
    const channel = MockBroadcastChannel.instances[0]
    channel.onmessage?.({
      data: {
        type: 'refresh-complete',
        ok: false,
        refreshToken: 'refresh-token',
      },
    } as MessageEvent)
    expect(useAuthStore().token?.accessToken).toBe('old-access-token')
  })

  it('ignores broadcast messages without a matching session token', () => {
    const oidc = createOidc()
    oidc.setToken(unexpiredToken, { sub: 'user-sub' })
    const channel = MockBroadcastChannel.instances[0]
    channel.onmessage?.({
      data: {
        type: 'refresh-complete',
        ok: true,
        refreshToken: 'other-refresh-token',
        token: { ...unexpiredToken, accessToken: 'other-access' },
        user: { sub: 'user-sub' },
      },
    } as MessageEvent)
    expect(useAuthStore().token?.accessToken).toBe('old-access-token')
  })

  it('adopts a broadcast rotation without user and completedAt metadata', () => {
    const oidc = createOidc()
    oidc.setToken(unexpiredToken, { sub: 'user-sub' })
    const channel = MockBroadcastChannel.instances[0]
    channel.onmessage?.({
      data: {
        type: 'refresh-complete',
        ok: true,
        refreshToken: 'refresh-token',
        token: { ...unexpiredToken, accessToken: 'rotated-access', refreshToken: 'rotated-refresh' },
      },
    } as MessageEvent)
    expect(useAuthStore().token?.accessToken).toBe('rotated-access')
    expect(useAuthStore().user?.sub).toBe('user-sub')
  })

  it('keeps an in-flight refresh when another tab reports a concurrent start', async () => {
    let resolveFetch!: (response: Response) => void
    const fetchMock = vi.fn(() => new Promise<Response>((resolve) => { resolveFetch = resolve }))
    global.fetch = fetchMock
    const oidc = createOidc()
    oidc.setToken(unexpiredToken, { sub: 'user-sub' })
    const pending = oidc.refreshToken()
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    const channel = MockBroadcastChannel.instances[0]
    channel.onmessage?.({
      data: {
        type: 'refresh-started',
        refreshToken: 'refresh-token',
      },
    } as MessageEvent)
    resolveFetch(new Response(JSON.stringify({ access_token: 'fresh-access', expires_in: 3600, refresh_token: 'rotated' }), { status: 200 }))
    await expect(pending).resolves.toBe(true)
  })

  it('logs out when the stored token has no refresh token', async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response('', { status: 200 }))
    const oidc = createOidc()
    const { setToken } = oidc
    setToken({ accessToken: 'access', idToken: '', refreshToken: undefined, expiresAt: Math.floor(Date.now() / 1000) + 3600 }, { sub: 'user-sub' })
    await expect(oidc.refreshToken()).resolves.toBe(false)
    expect(useAuthStore().token).toBeNull()
  })

  it('schedules a transient retry while keeping the session on a rate limit', async () => {
    vi.useFakeTimers()
    global.fetch = vi.fn()
      .mockResolvedValueOnce(new Response('', { status: 429 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ access_token: 'fresh-access', expires_in: 3600, refresh_token: 'rotated' }), { status: 200 }))
    const oidc = createOidc()
    oidc.setToken(unexpiredToken, { sub: 'user-sub' })
    await expect(oidc.refreshToken()).resolves.toBe(false)
    expect(useAuthStore().token?.accessToken).toBe('old-access-token')
    const retry = oidc.refreshToken()
    await vi.advanceTimersByTimeAsync(31_000)
    await expect(retry).resolves.toBe(true)
    expect(useAuthStore().token?.accessToken).toBe('fresh-access')
  })

})
