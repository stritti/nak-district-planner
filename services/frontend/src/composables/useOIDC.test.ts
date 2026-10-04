import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '../stores/auth'
import {
  MockBroadcastChannel,
  postedBroadcastMessages,
  resetBroadcastChannelMocks,
} from '../testing/broadcastChannel'
import { stubNoWebLocks, stubWebLocks } from '../testing/webLocks'
import { REFRESH_SESSION_COORDINATION_ID } from './oidcToken'
import { __resetOIDCModuleState, useOIDC } from './useOIDC'

const routerPush = vi.fn().mockResolvedValue(undefined)

vi.mock('vue-router', () => ({
  createRouter: vi.fn(),
  createWebHistory: vi.fn(),
  useRouter: () => ({ push: routerPush }),
}))

function jwt(claims: Record<string, unknown>): string {
  const payload = btoa(JSON.stringify(claims))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '')
  return `header.${payload}.signature`
}

function discoveryResponse(): Response {
  return new Response(JSON.stringify({
    authorization_endpoint: 'https://idp.example/authorize',
    token_endpoint: 'https://idp.example/token',
    userinfo_endpoint: 'https://idp.example/userinfo',
    revocation_endpoint: 'https://idp.example/revoke',
    client_id: 'planner-client',
  }), { status: 200 })
}

function refreshResponse(accessToken = 'next-access'): Response {
  return new Response(JSON.stringify({
    access_token: accessToken,
    refresh_session: true,
    expires_in: 3600,
  }), { status: 200 })
}

function createOidc() {
  return useOIDC(undefined, {
    redirectUri: 'http://localhost:5173/auth/callback',
    scope: 'openid profile email',
  })
}

function activeToken(accessToken = 'current-access') {
  return {
    accessToken,
    idToken: '',
    refreshToken: REFRESH_SESSION_COORDINATION_ID,
    expiresAt: Math.floor(Date.now() / 1000) + 3600,
  }
}

beforeEach(() => {
  __resetOIDCModuleState()
  resetBroadcastChannelMocks()
  stubWebLocks()
  setActivePinia(createPinia())
  sessionStorage.clear()
  localStorage.clear()
  document.cookie = 'csrf_token=oidc-csrf; Path=/'
  routerPush.mockClear()
  vi.clearAllMocks()
})

afterEach(() => {
  document.cookie = 'csrf_token=; Max-Age=0; Path=/'
  vi.useRealTimers()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('authorization', () => {
  it('creates a PKCE authorization URL and keeps verifier/state tab-local', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(discoveryResponse()))
    const oidc = createOidc()

    const url = new URL(await oidc.getAuthorizationUrl())

    expect(url.origin + url.pathname).toBe('https://idp.example/authorize')
    expect(url.searchParams.get('client_id')).toBe('planner-client')
    expect(url.searchParams.get('response_type')).toBe('code')
    expect(url.searchParams.get('code_challenge_method')).toBe('S256')
    expect(url.searchParams.get('code_challenge')).toBeTruthy()
    expect(url.searchParams.get('state')).toBeTruthy()
    expect(sessionStorage.getItem('oidc_code_verifier')).toBeTruthy()
    expect(sessionStorage.getItem('oidc_state')).toBe(url.searchParams.get('state'))
    expect(localStorage.length).toBe(0)
  })

  it('rejects a code exchange when the PKCE verifier is missing', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(discoveryResponse()))
    const oidc = createOidc()

    await expect(oidc.exchangeCodeForToken('code')).rejects.toThrow('Code verifier not found')
  })

  it('installs a memory-only session from a successful code exchange', async () => {
    const idToken = jwt({ sub: 'user-1', email: 'u@example.org' })
    sessionStorage.setItem('oidc_code_verifier', 'verifier')
    sessionStorage.setItem('oidc_state', 'state')
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
      if (String(input) === '/api/v1/auth/oidc/discovery') {
        return Promise.resolve(discoveryResponse())
      }
      return Promise.resolve(new Response(JSON.stringify({
        access_token: 'access-from-code',
        id_token: idToken,
        refresh_session: true,
        expires_in: 1800,
      }), { status: 200 }))
    }))
    const oidc = createOidc()

    await oidc.exchangeCodeForToken('code')

    const auth = useAuthStore()
    expect(auth.token).toEqual(expect.objectContaining({
      accessToken: 'access-from-code',
      refreshToken: REFRESH_SESSION_COORDINATION_ID,
    }))
    expect(auth.user).toEqual(expect.objectContaining({ sub: 'user-1', email: 'u@example.org' }))
    expect(sessionStorage.getItem('oidc_code_verifier')).toBeNull()
    expect(sessionStorage.getItem('oidc_state')).toBeNull()
    expect(localStorage.length).toBe(0)
  })
})

describe('refresh coordination', () => {
  it('shares one in-flight refresh across callers in the same tab', async () => {
    let resolveRefresh!: (response: Response) => void
    const fetchMock = vi.fn(() => new Promise<Response>((resolve) => {
      resolveRefresh = resolve
    }))
    vi.stubGlobal('fetch', fetchMock)
    const oidc = createOidc()
    oidc.setToken(activeToken(), { sub: 'user-1' })

    const first = oidc.refreshToken()
    const second = oidc.refreshToken()
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    resolveRefresh(refreshResponse())

    await expect(Promise.all([first, second])).resolves.toEqual([true, true])
    expect(useAuthStore().token?.accessToken).toBe('next-access')
  })

  it('does not let a stale refresh overwrite a logout', async () => {
    let resolveRefresh!: (response: Response) => void
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      if (String(input) === '/api/v1/auth/oidc/revoke') {
        return Promise.resolve(new Response('', { status: 204 }))
      }
      return new Promise<Response>((resolve) => { resolveRefresh = resolve })
    })
    vi.stubGlobal('fetch', fetchMock)
    const oidc = createOidc()
    oidc.setToken(activeToken(), { sub: 'user-1' })

    const pending = oidc.refreshToken()
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/auth/oidc/token',
      expect.anything(),
    ))
    await oidc.logout()
    resolveRefresh(refreshResponse('stale-access'))

    await expect(pending).resolves.toBe(false)
    expect(useAuthStore().token).toBeNull()
  })

  it('does not let a stale refresh overwrite a replacement identity', async () => {
    let resolveRefresh!: (response: Response) => void
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>((resolve) => {
      resolveRefresh = resolve
    })))
    const oidc = createOidc()
    oidc.setToken(activeToken(), { sub: 'old-user' })

    const pending = oidc.refreshToken()
    await vi.waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1))
    oidc.setToken(activeToken('replacement-access'), { sub: 'new-user' })
    resolveRefresh(refreshResponse('stale-access'))

    await expect(pending).resolves.toBe(false)
    expect(useAuthStore().token?.accessToken).toBe('replacement-access')
    expect(useAuthStore().user?.sub).toBe('new-user')
  })

  it('adopts a successful refresh broadcast for the same in-memory session', () => {
    const oidc = createOidc()
    oidc.setToken(activeToken(), { sub: 'user-1' })
    const channel = MockBroadcastChannel.instances[0]

    channel.onmessage?.({
      data: {
        type: 'refresh-complete',
        ok: true,
        sessionId: REFRESH_SESSION_COORDINATION_ID,
        token: activeToken('broadcast-access'),
        user: { sub: 'user-1' },
        completedAt: 200,
      },
    } as MessageEvent)

    expect(useAuthStore().token?.accessToken).toBe('broadcast-access')
  })

  it('ignores broadcasts for another session and older completions', () => {
    const oidc = createOidc()
    oidc.setToken(activeToken(), { sub: 'user-1' })
    const channel = MockBroadcastChannel.instances[0]

    channel.onmessage?.({
      data: {
        type: 'refresh-complete',
        ok: true,
        sessionId: REFRESH_SESSION_COORDINATION_ID,
        token: activeToken('newest'),
        completedAt: 200,
      },
    } as MessageEvent)
    channel.onmessage?.({
      data: {
        type: 'refresh-complete',
        ok: true,
        sessionId: REFRESH_SESSION_COORDINATION_ID,
        token: activeToken('older'),
        completedAt: 100,
      },
    } as MessageEvent)
    channel.onmessage?.({
      data: {
        type: 'refresh-complete',
        ok: true,
        sessionId: 'other-session',
        token: activeToken('other'),
        completedAt: 300,
      },
    } as MessageEvent)

    expect(useAuthStore().token?.accessToken).toBe('newest')
  })

  it('waits for a peer tab after a refresh-started broadcast', async () => {
    const oidc = createOidc()
    oidc.setToken(activeToken(), { sub: 'user-1' })
    const channel = MockBroadcastChannel.instances[0]

    channel.onmessage?.({
      data: {
        type: 'refresh-started',
        sessionId: REFRESH_SESSION_COORDINATION_ID,
      },
    } as MessageEvent)
    const waiting = oidc.refreshToken()
    channel.onmessage?.({
      data: {
        type: 'refresh-complete',
        ok: true,
        sessionId: REFRESH_SESSION_COORDINATION_ID,
        token: activeToken('peer-access'),
        user: { sub: 'user-1' },
        completedAt: Date.now(),
      },
    } as MessageEvent)

    await expect(waiting).resolves.toBe(true)
    expect(useAuthStore().token?.accessToken).toBe('peer-access')
  })

  it('publishes only a non-secret session identifier during refresh', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(refreshResponse()))
    const oidc = createOidc()
    oidc.setToken(activeToken(), { sub: 'user-1' })

    await expect(oidc.refreshToken()).resolves.toBe(true)

    expect(postedBroadcastMessages).toContainEqual({
      type: 'refresh-started',
      sessionId: REFRESH_SESSION_COORDINATION_ID,
    })
    expect(JSON.stringify(postedBroadcastMessages)).not.toContain('provider-refresh')
    expect(localStorage.length).toBe(0)
    expect(sessionStorage.length).toBe(0)
  })

  it('fails closed after expiry when Web Locks are unavailable', async () => {
    stubNoWebLocks()
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
      if (String(input) === '/api/v1/auth/oidc/revoke') {
        return Promise.resolve(new Response('', { status: 204 }))
      }
      return Promise.resolve(refreshResponse())
    }))
    const oidc = createOidc()
    oidc.setToken({
      ...activeToken(),
      expiresAt: Math.floor(Date.now() / 1000) - 1,
    }, { sub: 'user-1' })

    await expect(oidc.refreshToken()).resolves.toBe(false)
    await vi.waitFor(() => expect(useAuthStore().token).toBeNull())
    expect(global.fetch).not.toHaveBeenCalledWith('/api/v1/auth/oidc/token', expect.anything())
  })
})

describe('session lifecycle', () => {
  it('logs out locally and revokes the server-held refresh cookie through the backend', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('', { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)
    const oidc = createOidc()
    oidc.setToken(activeToken(), { sub: 'user-1' })

    await oidc.logout()

    expect(useAuthStore().token).toBeNull()
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/auth/oidc/revoke',
      expect.objectContaining({
        method: 'POST',
        headers: { 'X-CSRF-Token': 'oidc-csrf' },
      }),
    )
    expect(routerPush).toHaveBeenCalledWith('/login')
  })

  it('restores a memory-only session during initialize when the HttpOnly cookie is valid', async () => {
    const restoredIdToken = jwt({ sub: 'restored-user' })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      access_token: 'restored-access',
      id_token: restoredIdToken,
      refresh_session: true,
      expires_in: 3600,
    }), { status: 200 })))
    const oidc = createOidc()

    oidc.initialize()

    await vi.waitFor(() => expect(useAuthStore().token?.accessToken).toBe('restored-access'))
    expect(useAuthStore().user?.sub).toBe('restored-user')
    expect(useAuthStore().token?.refreshToken).toBe(REFRESH_SESSION_COORDINATION_ID)
    expect(localStorage.length).toBe(0)
  })

  it('keeps computed auth state synchronized with the in-memory store', () => {
    const oidc = createOidc()
    expect(oidc.isAuthenticated.value).toBe(false)
    expect(oidc.isTokenExpired.value).toBe(true)

    oidc.setToken(activeToken(), { sub: 'user-1' })

    expect(oidc.isAuthenticated.value).toBe(true)
    expect(oidc.isTokenExpired.value).toBe(false)
    expect(oidc.token.value?.accessToken).toBe('current-access')
    expect(oidc.user.value?.sub).toBe('user-1')
  })
})
