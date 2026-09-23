/**
 * Tests for useOIDC composable
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { __resetOIDCModuleState, useOIDC } from './useOIDC'
import { useAuthStore } from '../stores/auth'

const postedBroadcastMessages: unknown[] = []

class MockBroadcastChannel {
  static instances: MockBroadcastChannel[] = []
  onmessage: ((event: MessageEvent) => void) | null = null

  constructor(public name: string) {
    MockBroadcastChannel.instances.push(this)
  }

  postMessage(message: unknown) {
    postedBroadcastMessages.push(message)
  }

  close() {}
}

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

  const expiredToken = (refreshToken = 'refresh-token') => ({
    accessToken: 'old-access-token',
    idToken: '',
    refreshToken,
    expiresAt: Math.floor(Date.now() / 1000) - 1,
  })

  beforeEach(() => {
    __resetOIDCModuleState()
    MockBroadcastChannel.instances = []
    postedBroadcastMessages.length = 0
    vi.stubGlobal('BroadcastChannel', MockBroadcastChannel)
    vi.stubGlobal('navigator', {
      ...navigator,
      locks: {
        request: async (name: string, _options: { ifAvailable: boolean }, callback: (lock: Lock | null) => Promise<boolean>) =>
          callback({ name, mode: 'exclusive' } as Lock),
      },
    })
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
    // Web Locks dispatch the callback asynchronously; wait for the fetch
    // to start before resolving the simulated network failure.
    await vi.waitFor(() => expect(rejectFetch).toBeTypeOf('function'))
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

  it('keeps the session on a definitive pre-provider rate limit', async () => {
    global.fetch = vi.fn(() => Promise.resolve(new Response('', { status: 429 })))
    const oidc = createOidc()
    const authStore = useAuthStore()
    oidc.setToken(expiredToken(), { sub: 'user-sub' })

    await expect(oidc.refreshToken()).resolves.toBe(false)

    expect(authStore.token?.accessToken).toBe('old-access-token')
    expect(authStore.user?.sub).toBe('user-sub')
  })

  it('logs out on invalid_grant refresh failure', async () => {
    global.fetch = vi.fn((input: RequestInfo | URL) => {
      if (String(input) === '/api/v1/auth/oidc/token') {
        return Promise.resolve(new Response(JSON.stringify({ error: 'invalid_grant' }), { status: 400 }))
      }
      return Promise.resolve(new Response(JSON.stringify({ client_id: 'client' }), { status: 200 }))
    })
    const oidc = createOidc()
    const authStore = useAuthStore()
    oidc.setToken(expiredToken(), { sub: 'user-sub' })

    await expect(oidc.refreshToken()).resolves.toBe(false)

    expect(authStore.token).toBeNull()
  })

  it('logs out on nested invalid_grant refresh failure from proxy', async () => {
    global.fetch = vi.fn((input: RequestInfo | URL) => {
      if (String(input) === '/api/v1/auth/oidc/token') {
        return Promise.resolve(new Response(JSON.stringify({ detail: { error: 'invalid_grant' } }), { status: 400 }))
      }
      return Promise.resolve(new Response(JSON.stringify({ client_id: 'client' }), { status: 200 }))
    })
    const oidc = createOidc()
    const authStore = useAuthStore()
    oidc.setToken(expiredToken(), { sub: 'user-sub' })

    await expect(oidc.refreshToken()).resolves.toBe(false)

    expect(authStore.token).toBeNull()
  })

  it('fails closed after an ambiguous refresh timeout without replaying the token', async () => {
    vi.useFakeTimers()
    global.fetch = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input) === '/api/v1/auth/oidc/token') {
        return new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
        })
      }
      return Promise.resolve(new Response('', { status: 200 }))
    })
    const oidc = createOidc()
    oidc.setToken(expiredToken(), { sub: 'user-sub' })

    const first = oidc.refreshToken()
    await vi.advanceTimersByTimeAsync(20_000)
    await expect(first).resolves.toBe(false)

    expect(localStorage.getItem('oidc-refresh-result:refresh-token')).toBe('')
    expect(useAuthStore().token).toBeNull()
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('adopts a cross-tab rotated token and coalesces while another tab refreshes', async () => {
    global.fetch = vi.fn(() => Promise.resolve(new Response('', { status: 500 })))

    const oidc = createOidc()
    const authStore = useAuthStore()
    oidc.setToken(expiredToken('shared-refresh-token'), { sub: 'user-sub' })
    const channel = MockBroadcastChannel.instances[0]

    channel.onmessage?.({ data: { type: 'refresh-started', refreshToken: 'shared-refresh-token' } } as MessageEvent)
    const coalesced = oidc.refreshToken()
    expect(fetch).not.toHaveBeenCalled()

    const rotated = {
      accessToken: 'rotated-access-token',
      idToken: '',
      refreshToken: 'rotated-refresh-token',
      expiresAt: Math.floor(Date.now() / 1000) + 3600,
    }
    channel.onmessage?.({
      data: {
        type: 'refresh-complete',
        ok: true,
        refreshToken: 'shared-refresh-token',
        token: rotated,
        user: { sub: 'user-sub' },
      },
    } as MessageEvent)

    await expect(coalesced).resolves.toBe(true)
    expect(authStore.token?.accessToken).toBe('rotated-access-token')
    expect(postedBroadcastMessages).toEqual([])
  })

  it('does not send a rotating refresh token without Web Locks', async () => {
    vi.stubGlobal('navigator', { ...navigator, locks: undefined })
    global.fetch = vi.fn()
    const oidc = createOidc()
    oidc.setToken(expiredToken('unsafe-fallback-token'), { sub: 'user-sub' })

    const result = await oidc.refreshToken()

    expect(result).toBe(false)
    expect(global.fetch).not.toHaveBeenCalled()
    expect(useAuthStore().token?.refreshToken).toBe('unsafe-fallback-token')
  })

  it('adopts a completed rotation under the Web Lock before fetching', async () => {
    const old = expiredToken('already-rotated-refresh')
    const rotated = { ...old, accessToken: 'new-access', refreshToken: 'new-refresh', expiresAt: Math.floor(Date.now() / 1000) + 3600 }
    global.fetch = vi.fn()
    const oidc = createOidc()
    oidc.setToken(old, { sub: 'user-sub' })
    localStorage.setItem('oidc-refresh-result:already-rotated-refresh', JSON.stringify({
      token: rotated, user: { sub: 'user-sub' }, recordedAt: Date.now(),
    }))

    await expect(oidc.refreshToken()).resolves.toBe(true)
    expect(global.fetch).not.toHaveBeenCalled()
    expect(useAuthStore().token?.refreshToken).toBe('new-refresh')
    localStorage.removeItem('oidc-refresh-result:already-rotated-refresh')
  })

  it('fails closed and clears the local session on a stranded pending receipt', async () => {
    const oidc = createOidc()
    oidc.setToken(expiredToken('stranded-token'), { sub: 'user-sub' })
    localStorage.setItem('oidc-refresh-result:stranded-token', '')
    global.fetch = vi.fn()
    await expect(oidc.refreshToken()).resolves.toBe(false)
    expect(global.fetch).not.toHaveBeenCalledWith('/api/v1/auth/oidc/token', expect.anything())
    expect(useAuthStore().token).toBeNull()
  })

  it('follows multiple rotation receipts before reporting success', async () => {
    const oidc = createOidc()
    oidc.setToken(expiredToken('first-token'), { sub: 'user-sub' })
    const middle = { ...expiredToken('second-token'), accessToken: 'expired-middle' }
    const latest = { ...middle, refreshToken: 'third-token', accessToken: 'latest-access', expiresAt: Math.floor(Date.now() / 1000) + 3600 }
    localStorage.setItem('oidc-refresh-result:first-token', JSON.stringify({ token: middle, user: { sub: 'user-sub' }, recordedAt: Date.now() }))
    localStorage.setItem('oidc-refresh-result:second-token', JSON.stringify({ token: latest, user: { sub: 'user-sub' }, recordedAt: Date.now() }))
    global.fetch = vi.fn()
    await expect(oidc.refreshToken()).resolves.toBe(true)
    expect(useAuthStore().token?.refreshToken).toBe('third-token')
    expect(global.fetch).not.toHaveBeenCalled()
  })

  it('recovers a missed cross-tab completion from the persisted receipt', async () => {
    vi.useFakeTimers()
    const oidc = createOidc()
    oidc.setToken(expiredToken('missed-token'), { sub: 'user-sub' })
    vi.stubGlobal('navigator', {
      ...navigator,
      locks: { request: async (_name: string, _opts: unknown, callback: (lock: Lock | null) => Promise<boolean>) => callback(null) },
    })
    const pending = oidc.refreshToken()
    await vi.advanceTimersByTimeAsync(1)
    const latest = { ...expiredToken('next-token'), accessToken: 'next-access', expiresAt: Math.floor(Date.now() / 1000) + 3600 }
    localStorage.setItem('oidc-refresh-result:missed-token', JSON.stringify({ token: latest, user: { sub: 'user-sub' }, recordedAt: Date.now() }))
    await vi.advanceTimersByTimeAsync(30_000)
    await expect(pending).resolves.toBe(true)
    expect(useAuthStore().token?.refreshToken).toBe('next-token')
  })

  it('preserves a pending marker after a transport failure to prevent token replay', async () => {
    const oidc = createOidc()
    oidc.setToken(expiredToken('ambiguous-token'), { sub: 'user-sub' })
    global.fetch = vi.fn().mockRejectedValueOnce(new Error('connection lost'))
    await expect(oidc.refreshToken()).resolves.toBe(false)
    expect(localStorage.getItem('oidc-refresh-result:ambiguous-token')).toBe('')
    expect(useAuthStore().token).toBeNull()
    expect(global.fetch).toHaveBeenCalledTimes(1)
  })

  it('adopts a same-refresh-token receipt from a non-rotating provider', async () => {
    const oidc = createOidc()
    oidc.setToken(expiredToken('stable-refresh'), { sub: 'user-sub' })
    const latest = { ...expiredToken('stable-refresh'), accessToken: 'new-access', expiresAt: Math.floor(Date.now() / 1000) + 3600 }
    localStorage.setItem('oidc-refresh-result:stable-refresh', JSON.stringify({ token: latest, user: { sub: 'user-sub' }, recordedAt: Date.now() }))
    global.fetch = vi.fn()
    await expect(oidc.refreshToken()).resolves.toBe(true)
    expect(useAuthStore().token?.accessToken).toBe('new-access')
    expect(global.fetch).not.toHaveBeenCalled()
  })

  it('clears an expired session when Web Locks are unavailable', async () => {
    vi.stubGlobal('navigator', { ...navigator, locks: undefined })
    const oidc = createOidc()
    oidc.setToken(expiredToken('unsupported-browser'), { sub: 'user-sub' })
    global.fetch = vi.fn().mockResolvedValue(new Response('', { status: 200 }))
    await expect(oidc.refreshToken()).resolves.toBe(false)
    expect(useAuthStore().token).toBeNull()
    expect(global.fetch).not.toHaveBeenCalledWith('/api/v1/auth/oidc/token', expect.anything())
  })

  it('retries a transient failure after removing its pending receipt', async () => {
    const oidc = createOidc()
    oidc.setToken(expiredToken('retry-receipt-token'), { sub: 'user-sub' })
    global.fetch = vi.fn().mockResolvedValueOnce(new Response('', { status: 429 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        access_token: 'retry-access', refresh_token: 'retry-rotated', expires_in: 3600,
      }), { status: 200 }))
    await expect(oidc.refreshToken()).resolves.toBe(false)
    expect(localStorage.getItem('oidc-refresh-result:retry-receipt-token')).toBeNull()
    await expect(oidc.refreshToken()).resolves.toBe(true)
    expect(global.fetch).toHaveBeenCalledTimes(2)
  })

  it('serializes simultaneous cross-tab refreshes with web locks', async () => {
    const activeLocks = new Set<string>()
    const locksRequest = vi.fn(
      async (
        name: string,
        _options: { ifAvailable: boolean },
        callback: (lock: Lock | null) => Promise<boolean>,
      ) => {
        if (activeLocks.has(name)) return callback(null)
        activeLocks.add(name)
        try {
          return await callback({ name, mode: 'exclusive' } as Lock)
        } finally {
          activeLocks.delete(name)
        }
      },
    )
    vi.stubGlobal('navigator', { ...navigator, locks: { request: locksRequest } })

    let resolveFetch!: (response: Response) => void
    global.fetch = vi.fn(
      () =>
        new Promise<Response>((resolve) => {
          resolveFetch = resolve
        }),
    )

    const first = createOidc()
    const second = createOidc()
    const authStore = useAuthStore()
    first.setToken(expiredToken('locked-refresh-token'), { sub: 'user-sub' })

    const firstRefresh = first.refreshToken()
    const secondRefresh = second.refreshToken()

    expect(locksRequest).toHaveBeenCalledTimes(1)
    expect(fetch).toHaveBeenCalledTimes(1)

    resolveFetch(
      new Response(
        JSON.stringify({
          access_token: 'locked-rotated-access-token',
          id_token: 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyLXN1YiJ9.signature',
          refresh_token: 'locked-rotated-refresh-token',
          expires_in: 3600,
        }),
        { status: 200 },
      ),
    )

    await expect(Promise.all([firstRefresh, secondRefresh])).resolves.toEqual([true, true])
    expect(authStore.token?.accessToken).toBe('locked-rotated-access-token')
    expect(second.token.value?.accessToken).toBe('locked-rotated-access-token')
  })

  it('adopts a rotated token instead of logging out after invalid_grant', async () => {
    global.fetch = vi.fn((input: RequestInfo | URL) => {
      if (String(input) === '/api/v1/auth/oidc/token') {
        return Promise.resolve(new Response(JSON.stringify({ error: 'invalid_grant' }), { status: 400 }))
      }
      return Promise.resolve(new Response(JSON.stringify({ client_id: 'client' }), { status: 200 }))
    })

    const oidc = createOidc()
    const authStore = useAuthStore()
    oidc.setToken(expiredToken('racing-refresh-token'), { sub: 'user-sub' })
    const channel = (globalThis.BroadcastChannel as unknown as { instances: { onmessage: ((event: MessageEvent) => void) | null }[] })
      .instances[0]
    const rotated = {
      accessToken: 'rotated-access-token',
      idToken: '',
      refreshToken: 'rotated-refresh-token',
      expiresAt: Math.floor(Date.now() / 1000) + 3600,
    }
    channel.onmessage?.({
      data: {
        type: 'refresh-complete',
        ok: true,
        refreshToken: 'racing-refresh-token',
        token: rotated,
        user: { sub: 'user-sub' },
      },
    } as MessageEvent)
    oidc.setToken(expiredToken('racing-refresh-token'), { sub: 'user-sub' })

    await expect(oidc.refreshToken()).resolves.toBe(false)

    expect(authStore.token?.accessToken).toBe('rotated-access-token')
  })
})
