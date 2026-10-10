// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

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
  useRouter: () => ({ push: vi.fn().mockResolvedValue(undefined) }),
}))

function tokenWithClaims(claims: unknown): string {
  const payload = btoa(JSON.stringify(claims))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '')
  return `header.${payload}.signature`
}

function discoveryResponse(overrides: Record<string, unknown> = {}): Response {
  return new Response(JSON.stringify({
    authorization_endpoint: 'https://auth.example.com/authorize',
    token_endpoint: 'https://auth.example.com/token',
    userinfo_endpoint: 'https://auth.example.com/userinfo',
    revocation_endpoint: 'https://auth.example.com/revoke',
    client_id: 'frontend-test-client',
    ...overrides,
  }), { status: 200 })
}

function refreshedResponse(accessToken = 'fresh-access'): Response {
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
})

afterEach(() => {
  document.cookie = 'csrf_token=; Max-Age=0; Path=/'
  vi.useRealTimers()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

async function exchangeWithResponse(body: unknown, status = 200): Promise<void> {
  sessionStorage.setItem('oidc_code_verifier', 'test-verifier')
  vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
    if (String(input) === '/api/v1/auth/oidc/discovery') {
      return Promise.resolve(discoveryResponse())
    }
    const bodyText = typeof body === 'string' ? body : JSON.stringify(body)
    return Promise.resolve(new Response(bodyText, { status }))
  }))
  await createOidc().exchangeCodeForToken('auth-code')
}

describe('token exchange validation', () => {
  it('stores only the non-secret server session coordination id', async () => {
    const idToken = tokenWithClaims({
      sub: 'user-sub',
      email: 'user@example.org',
      name: 'Test User',
    })

    await exchangeWithResponse({
      access_token: 'new-access-token',
      id_token: idToken,
      refresh_session: true,
      expires_in: 3600,
    })

    const auth = useAuthStore()
    expect(auth.token).toEqual(expect.objectContaining({
      accessToken: 'new-access-token',
      refreshToken: REFRESH_SESSION_COORDINATION_ID,
      idToken,
    }))
    expect(auth.user).toEqual(expect.objectContaining({
      sub: 'user-sub',
      email: 'user@example.org',
    }))
    expect(localStorage.length).toBe(0)
  })

  it.each([
    { access_token: '' },
    { access_token: 42 },
    { access_token: 'access', expires_in: '3600' },
    { access_token: 'access', expires_in: 0 },
    { access_token: 'access', refresh_session: 'yes' },
  ])('rejects malformed token response %#', async (body) => {
    await expect(exchangeWithResponse(body)).rejects.toThrow('Token response missing or malformed access_token')
    expect(useAuthStore().token).toBeNull()
  })

  it('surfaces a backend exchange error without installing partial auth', async () => {
    await expect(exchangeWithResponse({ error: 'invalid_grant' }, 400))
      .rejects.toThrow('Token exchange failed (400)')
    expect(useAuthStore().token).toBeNull()
  })

  it('uses userinfo when token claims do not provide a subject', async () => {
    sessionStorage.setItem('oidc_code_verifier', 'test-verifier')
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
      if (String(input) === '/api/v1/auth/oidc/discovery') {
        return Promise.resolve(discoveryResponse())
      }
      if (String(input) === 'https://auth.example.com/userinfo') {
        return Promise.resolve(new Response(JSON.stringify({
          sub: 'userinfo-sub',
          email: 'userinfo@example.org',
        }), { status: 200 }))
      }
      return Promise.resolve(refreshedResponse('opaque-access'))
    }))

    await createOidc().exchangeCodeForToken('auth-code')

    expect(useAuthStore().user).toEqual(expect.objectContaining({
      sub: 'userinfo-sub',
      email: 'userinfo@example.org',
    }))
  })

  it.each([
    new Response('[1,2,3]', { status: 200 }),
    new Response(JSON.stringify({ sub: 42 }), { status: 200 }),
    new Response('provider failure', { status: 500 }),
  ])('rejects exchange when userinfo cannot establish an identity', async (userinfoResponse) => {
    sessionStorage.setItem('oidc_code_verifier', 'test-verifier')
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
      if (String(input) === '/api/v1/auth/oidc/discovery') {
        return Promise.resolve(discoveryResponse())
      }
      if (String(input) === 'https://auth.example.com/userinfo') {
        return Promise.resolve(userinfoResponse.clone())
      }
      return Promise.resolve(refreshedResponse('opaque-access'))
    }))

    await expect(createOidc().exchangeCodeForToken('auth-code')).rejects.toThrow('OIDC identity missing')
    expect(useAuthStore().token).toBeNull()
  })
})

describe('discovery', () => {
  it('shares one in-flight discovery request across callers', async () => {
    let resolveDiscovery!: (response: Response) => void
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>((resolve) => {
      resolveDiscovery = resolve
    })))
    const oidc = createOidc()

    const first = oidc.loadDiscovery()
    const second = oidc.loadDiscovery()
    resolveDiscovery(discoveryResponse())
    await Promise.all([first, second])

    expect(global.fetch).toHaveBeenCalledTimes(1)
  })

  it('reuses an already loaded discovery document', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(discoveryResponse()))
    const oidc = createOidc()

    await oidc.loadDiscovery()
    await oidc.loadDiscovery()

    expect(global.fetch).toHaveBeenCalledTimes(1)
  })

  it('rejects discovery documents without required endpoints', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ client_id: 'client' }),
      { status: 200 },
    )))
    const oidc = createOidc()

    await expect(oidc.loadDiscovery()).rejects.toThrow('misses required endpoints')
    expect(oidc.error.value).toContain('misses required endpoints')
  })

  it('rejects discovery documents without the proxied client id', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(discoveryResponse({ client_id: undefined })))

    await expect(createOidc().loadDiscovery()).rejects.toThrow('client ID not provided')
  })

  it('reports HTTP discovery failures', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('unavailable', { status: 503 })))
    const oidc = createOidc()

    await expect(oidc.loadDiscovery()).rejects.toThrow('OIDC discovery failed (503)')
    expect(oidc.error.value).toContain('OIDC discovery failed (503)')
  })
})

describe('runtime refresh triggers', () => {
  it('refreshes on user activity when the access token is close to expiry', async () => {
    const fetchMock = vi.fn().mockResolvedValue(refreshedResponse())
    vi.stubGlobal('fetch', fetchMock)
    const oidc = createOidc()
    oidc.setToken({
      ...unexpiredToken,
      expiresAt: Math.floor(Date.now() / 1000) + 60,
    }, { sub: 'user-sub' })

    oidc.initialize()
    document.dispatchEvent(new Event('mousemove'))

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/auth/oidc/token',
      expect.anything(),
    ))
  })

  it('refreshes immediately during initialize when the access token is expired', async () => {
    const fetchMock = vi.fn().mockResolvedValue(refreshedResponse())
    vi.stubGlobal('fetch', fetchMock)
    const oidc = createOidc()
    oidc.setToken({
      ...unexpiredToken,
      expiresAt: Math.floor(Date.now() / 1000) - 10,
    }, { sub: 'user-sub' })

    oidc.initialize()

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/auth/oidc/token',
      expect.anything(),
    ))
  })

  it('keeps a valid token until expiry when Web Locks are unsupported', async () => {
    const { stubNoWebLocks } = await import('../testing/webLocks')
    stubNoWebLocks()
    vi.useFakeTimers()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 204 })))
    const oidc = createOidc()
    oidc.setToken({
      ...unexpiredToken,
      expiresAt: Math.floor(Date.now() / 1000) + 60,
    }, { sub: 'user-sub' })

    await expect(oidc.refreshToken()).resolves.toBe(false)
    expect(useAuthStore().token).not.toBeNull()
    await vi.advanceTimersByTimeAsync(61_000)
    expect(useAuthStore().token).toBeNull()
  })
})

describe('broadcast validation', () => {
  it('ignores malformed refreshed tokens', () => {
    const oidc = createOidc()
    oidc.setToken(unexpiredToken, { sub: 'user-sub' })
    const channel = MockBroadcastChannel.instances[0]

    channel.onmessage?.({
      data: {
        type: 'refresh-complete',
        ok: true,
        sessionId: REFRESH_SESSION_COORDINATION_ID,
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

  it('clears peer wait state on an unsuccessful completion', async () => {
    const oidc = createOidc()
    oidc.setToken(unexpiredToken, { sub: 'user-sub' })
    const channel = MockBroadcastChannel.instances[0]
    channel.onmessage?.({
      data: { type: 'refresh-started', sessionId: REFRESH_SESSION_COORDINATION_ID },
    } as MessageEvent)
    const waiting = oidc.refreshToken()

    channel.onmessage?.({
      data: {
        type: 'refresh-complete',
        ok: false,
        sessionId: REFRESH_SESSION_COORDINATION_ID,
      },
    } as MessageEvent)

    await expect(waiting).resolves.toBe(false)
    expect(useAuthStore().token?.accessToken).toBe('old-access-token')
  })
})
