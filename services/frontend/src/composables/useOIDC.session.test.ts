/**
 * Additional tests for useOIDC composable: token exchange validation,
 * userinfo validation, activity refresh, and initialization paths.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '../stores/auth'
import { MockBroadcastChannel, resetBroadcastChannelMocks } from '../testing/broadcastChannel'
import { stubWebLocks } from '../testing/webLocks'
import { REFRESH_SESSION_COORDINATION_ID } from './oidcToken'
import { __resetOIDCModuleState, useOIDC } from './useOIDC'

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

const refreshedResponse = (accessToken = 'fresh-access') => new Response(
  JSON.stringify({
    access_token: accessToken,
    refresh_session: true,
    expires_in: 3600,
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
    refreshToken: REFRESH_SESSION_COORDINATION_ID,
    expiresAt: Math.floor(Date.now() / 1000) + 3600,
  }

  beforeEach(() => {
    __resetOIDCModuleState()
    resetBroadcastChannelMocks()
    stubWebLocks()
    setActivePinia(createPinia())
    sessionStorage.clear()
    localStorage.clear()
    document.cookie = 'csrf_token=test-csrf; Path=/'
    vi.clearAllMocks()
    createOidc().setToken(null)
  })

  afterEach(() => {
    createOidc().setToken(null)
    document.cookie = 'csrf_token=; Max-Age=0; Path=/'
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
    const fetchMock = vi.fn(() => Promise.resolve(refreshedResponse()))
    global.fetch = fetchMock
    const oidc = createOidc()
    oidc.setToken(
      { ...unexpiredToken, expiresAt: Math.floor(Date.now() / 1000) + 60 },
      { sub: 'user-sub' },
    )
    oidc.initialize()
    document.dispatchEvent(new Event('mousemove'))
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/v1/auth/oidc/token', expect.anything()))
    document.dispatchEvent(new Event('keydown'))
    document.dispatchEvent(new Event('visibilitychange'))
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('treats a missing server refresh session as a normal logged-out initialize state', async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response('', { status: 401 }))
    const oidc = createOidc()

    expect(() => oidc.initialize()).not.toThrow()
    await vi.waitFor(() => expect(global.fetch).toHaveBeenCalledWith(
      '/api/v1/auth/oidc/token',
      expect.anything(),
    ))
    expect(useAuthStore().token).toBeNull()
  })

  it('stores the exchanged token and user without exposing a provider refresh token', async () => {
    const idToken = tokenWithClaims({ sub: 'user-sub', email: 'user@example.com', name: 'Test User' })
    const result = await exchangeWithResponse({
      access_token: 'new-access-token',
      id_token: idToken,
      refresh_session: true,
      expires_in: 3600,
    })
    expect(result).toBeUndefined()
    const authStore = useAuthStore()
    expect(authStore.token?.accessToken).toBe('new-access-token')
    expect(authStore.token?.refreshToken).toBe(REFRESH_SESSION_COORDINATION_ID)
    expect(authStore.token?.idToken).toBe(idToken)
    expect(authStore.user?.sub).toBe('user-sub')
    expect(authStore.user?.email).toBe('user@example.com')
    expect(sessionStorage.getItem('oidc_code_verifier')).toBeNull()
    expect(localStorage.length).toBe(0)
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
      return Promise.resolve(refreshedResponse('new-access-token'))
    })
    sessionStorage.setItem('oidc_code_verifier', 'test-verifier')
    const { exchangeCodeForToken } = createOidc()
    await exchangeCodeForToken('auth_code_123')
    const authStore = useAuthStore()
    expect(authStore.token?.accessToken).toBe('new-access-token')
    expect(authStore.token?.refreshToken).toBe(REFRESH_SESSION_COORDINATION_ID)
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
      return Promise.resolve(refreshedResponse('new-access-token'))
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

  it('propagates non-Error network rejections from the exchange', async () => {
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
      return Promise.resolve(refreshedResponse('new-access-token'))
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
      return Promise.resolve(refreshedResponse('new-access-token'))
    })
    sessionStorage.setItem('oidc_code_verifier', 'test-verifier')
    const { exchangeCodeForToken } = createOidc()
    await expect(exchangeCodeForToken('auth_code_123')).rejects.toThrow('OIDC identity missing')
  })

  it('ignores a malformed broadcast refresh instead of adopting it', () => {
    const oidc = createOidc()
    oidc.setToken(unexpiredToken, { sub: 'user-sub' })
    const channel = MockBroadcastChannel.instances[0]
    channel.onmessage?.({
      data: {
        type: 'refresh-complete',
        ok: true,
        refreshToken: REFRESH_SESSION_COORDINATION_ID,
        token: {
          accessToken: '',
          refreshToken: REFRESH_SESSION_COORDINATION_ID,
          idToken: '',
          expiresAt: 1,
        },
        user: { sub: 'user-sub' },
        completedAt: Date.now(),
      },
    } as MessageEvent)
    expect(useAuthStore().token?.accessToken).toBe('old-access-token')
  })

  it('revokes the server-held refresh session on logout', async () => {
    const fetchMock = vi.fn(() => Promise.resolve(new Response('', { status: 204 })))
    global.fetch = fetchMock
    const oidc = createOidc()
    oidc.setToken(unexpiredToken, { sub: 'user-sub' })
    await oidc.logout()
    expect(useAuthStore().token).toBeNull()
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/auth/oidc/revoke',
      expect.objectContaining({
        method: 'POST',
        headers: { 'X-CSRF-Token': 'test-csrf' },
      }),
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
    const oidc = createOidc()
    oidc.setToken(unexpiredToken, { sub: 'user-sub' })
    expect(() => oidc.initialize()).not.toThrow()
  })

  it('schedules a delayed logout for an unexpired token without Web Locks', async () => {
    const { stubNoWebLocks } = await import('../testing/webLocks')
    stubNoWebLocks()
    vi.useFakeTimers()
    global.fetch = vi.fn().mockResolvedValue(new Response('', { status: 204 }))
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
        return Promise.resolve(refreshedResponse())
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
      () => new Promise<Response>((resolve) => {
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

  it('keeps timer, activity, and session invalidation bound to the first composable instance', async () => {
    let tokenFetches = 0
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      if (String(input) === '/api/v1/auth/oidc/revoke') {
        return Promise.resolve(new Response('', { status: 204 }))
      }
      tokenFetches += 1
      return Promise.resolve(refreshedResponse(`fresh-${tokenFetches}`))
    })
    global.fetch = fetchMock
    const first = createOidc()
    const second = createOidc()
    first.setToken(
      { ...unexpiredToken, expiresAt: Math.floor(Date.now() / 1000) + 60 },
      { sub: 'user-sub' },
    )

    first.initialize()
    document.dispatchEvent(new Event('mousemove'))
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/v1/auth/oidc/token', expect.anything()))
    expect(useAuthStore().token?.accessToken).toBe('fresh-1')

    await second.logout()
    expect(useAuthStore().token).toBeNull()
  })

  it('binds module singletons only once across composable instances', () => {
    const first = createOidc()
    const second = createOidc()
    first.setToken(unexpiredToken, { sub: 'user-sub' })
    second.setToken(unexpiredToken, { sub: 'user-sub' })

    const generationAfterFirst = first.getSessionGeneration()
    expect(second.getSessionGeneration()).toBe(generationAfterFirst)
    expect(() => first.initialize()).not.toThrow()
    expect(() => second.initialize()).not.toThrow()
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
      return Promise.resolve(refreshedResponse('new-access-token'))
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
      return Promise.resolve(refreshedResponse('new-access-token'))
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
        refreshToken: REFRESH_SESSION_COORDINATION_ID,
      },
    } as MessageEvent)
    expect(useAuthStore().token?.accessToken).toBe('old-access-token')
  })

  it('ignores broadcast messages without a matching session coordination id', () => {
    const oidc = createOidc()
    oidc.setToken(unexpiredToken, { sub: 'user-sub' })
    const channel = MockBroadcastChannel.instances[0]
    channel.onmessage?.({
      data: {
        type: 'refresh-complete',
        ok: true,
        refreshToken: 'other-session',
        token: { ...unexpiredToken, accessToken: 'other-access' },
        user: { sub: 'user-sub' },
      },
    } as MessageEvent)
    expect(useAuthStore().token?.accessToken).toBe('old-access-token')
  })

  it('adopts a broadcast refresh without user and completedAt metadata', () => {
    const oidc = createOidc()
    oidc.setToken(unexpiredToken, { sub: 'user-sub' })
    const channel = MockBroadcastChannel.instances[0]
    channel.onmessage?.({
      data: {
        type: 'refresh-complete',
        ok: true,
        refreshToken: REFRESH_SESSION_COORDINATION_ID,
        token: {
          ...unexpiredToken,
          accessToken: 'refreshed-access',
          refreshToken: REFRESH_SESSION_COORDINATION_ID,
        },
      },
    } as MessageEvent)
    expect(useAuthStore().token?.accessToken).toBe('refreshed-access')
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
        refreshToken: REFRESH_SESSION_COORDINATION_ID,
      },
    } as MessageEvent)
    resolveFetch(refreshedResponse())
    await expect(pending).resolves.toBe(true)
  })

  it('logs out when the stored token has no refresh session coordination id', async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response('', { status: 204 }))
    const oidc = createOidc()
    oidc.setToken(
      {
        accessToken: 'access',
        idToken: '',
        refreshToken: undefined,
        expiresAt: Math.floor(Date.now() / 1000) + 3600,
      },
      { sub: 'user-sub' },
    )
    await expect(oidc.refreshToken()).resolves.toBe(false)
    expect(useAuthStore().token).toBeNull()
  })

  it('schedules a transient retry while keeping the session on a rate limit', async () => {
    vi.useFakeTimers()
    global.fetch = vi.fn()
      .mockResolvedValueOnce(new Response('', { status: 429 }))
      .mockResolvedValueOnce(refreshedResponse())
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
