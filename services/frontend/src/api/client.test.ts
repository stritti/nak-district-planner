import { describe, it, expect, vi, beforeEach } from 'vitest'
import { apiFetch } from './client'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '../stores/auth'
import { __resetOIDCModuleState, useOIDC } from '../composables/useOIDC'

// Mock useCSRF composable
vi.mock('../composables/useCSRF', () => ({
  useCSRF: () => ({
    getCSRFHeaders: () => ({ 'X-CSRF-Token': 'mock-csrf-token' }),
  }),
}))

function makeResponse(
  body: unknown,
  {
    status = 200,
    ok = true,
    contentLength = null as string | null,
  } = {},
) {
  return {
    ok,
    status,
    statusText: ok ? 'OK' : 'Error',
    headers: {
      get: (h: string) => (h === 'content-length' ? contentLength : null),
    },
    text: vi.fn().mockResolvedValue(typeof body === 'string' ? body : JSON.stringify(body)),
    json: vi.fn().mockResolvedValue(body),
  }
}

describe('apiFetch', () => {
  beforeEach(() => {
    __resetOIDCModuleState()
    vi.stubGlobal('fetch', vi.fn())
    vi.stubGlobal('navigator', {
      ...navigator,
      locks: {
        request: async (name: string, _options: { ifAvailable: boolean }, callback: (lock: Lock | null) => Promise<boolean>) =>
          callback({ name, mode: 'exclusive' } as Lock),
      },
    })
    setActivePinia(createPinia())
  })

  it('returns parsed JSON on success', async () => {
    const data = { id: '1', title: 'Test' }
    vi.mocked(fetch).mockResolvedValue(makeResponse(data) as unknown as Response)

    const result = await apiFetch<typeof data>('/api/v1/test')
    expect(result).toEqual(data)
  })

  it('includes Content-Type header', async () => {
    vi.mocked(fetch).mockResolvedValue(makeResponse({}) as unknown as Response)

    await apiFetch('/api/v1/test')

    const [, options] = vi.mocked(fetch).mock.calls[0]
    const headers = (options as RequestInit).headers as Record<string, string>
    expect(headers['Content-Type']).toBe('application/json')
  })

  it('includes Authorization header when token is present', async () => {
    const authStore = useAuthStore()
    const mockToken = {
      accessToken: 'test_token_123',
      idToken: 'test_id_token',
      expiresAt: Math.floor(Date.now() / 1000) + 3600,
    }
    authStore.setToken(mockToken)

    vi.mocked(fetch).mockResolvedValue(makeResponse({}) as unknown as Response)

    await apiFetch('/api/v1/test')

    const [, options] = vi.mocked(fetch).mock.calls[0]
    const headers = (options as RequestInit).headers as Record<string, string>
    expect(headers['Authorization']).toBe('Bearer test_token_123')
  })

  it('does not include Authorization header when no token', async () => {
    vi.mocked(fetch).mockResolvedValue(makeResponse({}) as unknown as Response)

    await apiFetch('/api/v1/test')

    const [, options] = vi.mocked(fetch).mock.calls[0]
    const headers = (options as RequestInit).headers as Record<string, string>
    expect(headers['Authorization']).toBeUndefined()
  })

  it('throws on non-ok response', async () => {
    vi.mocked(fetch).mockResolvedValue(
      makeResponse('Bad Request', { status: 400, ok: false }) as unknown as Response,
    )

    await expect(apiFetch('/api/v1/fail')).rejects.toThrow('400')
  })

  it('returns undefined for 204 No Content', async () => {
    vi.mocked(fetch).mockResolvedValue(
      makeResponse(null, { status: 204 }) as unknown as Response,
    )

    const result = await apiFetch('/api/v1/delete')
    expect(result).toBeUndefined()
  })

  it('returns undefined when content-length is 0', async () => {
    vi.mocked(fetch).mockResolvedValue(
      makeResponse(null, { contentLength: '0' }) as unknown as Response,
    )

    const result = await apiFetch('/api/v1/empty')
    expect(result).toBeUndefined()
  })

  it('merges extra headers from options', async () => {
    vi.mocked(fetch).mockResolvedValue(makeResponse({}) as unknown as Response)

    await apiFetch('/api/v1/test', { headers: { 'X-Custom': 'value' } })

    const [, options] = vi.mocked(fetch).mock.calls[0]
    const headers = (options as RequestInit).headers as Record<string, string>
    expect(headers['X-Custom']).toBe('value')
    expect(headers['Content-Type']).toBe('application/json')
  })

  it('aborts preflight when pending refresh is discarded after session replacement', async () => {
    const authStore = useAuthStore()
    authStore.setToken(
      {
        accessToken: 'old-access-token',
        idToken: '',
        refreshToken: 'old-refresh-token',
        expiresAt: Math.floor(Date.now() / 1000) - 1,
      },
      { sub: 'old-user-sub' },
    )

    let resolveRefresh!: (response: Response) => void
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      if (String(input) === '/api/v1/auth/oidc/token') {
        return new Promise<Response>((resolve) => {
          resolveRefresh = resolve
        })
      }

      return Promise.resolve(makeResponse({ ok: true }) as unknown as Response)
    })

    const request = apiFetch('/api/v1/state-changing', { method: 'POST' })

    // Web Lock dispatch is asynchronous; wait for the refresh request to
    // start before replacing the session.
    await vi.waitFor(() => expect(resolveRefresh).toBeTypeOf('function'))
    useOIDC().setToken(
      {
        accessToken: 'new-access-token',
        idToken: '',
        refreshToken: 'new-refresh-token',
        expiresAt: Math.floor(Date.now() / 1000) + 3600,
      },
      { sub: 'new-user-sub' },
    )
    resolveRefresh(
      new Response(
        JSON.stringify({
          access_token: 'refreshed-old-access-token',
          id_token: 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJvbGQtdXNlci1zdWIifQ.signature',
          expires_in: 3600,
        }),
        { status: 200 },
      ),
    )

    await expect(request).rejects.toThrow('Unauthorized')
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(authStore.token?.accessToken).toBe('new-access-token')
  })

  it('aborts a 401 retry when the initiating session was replaced while pending', async () => {
    const authStore = useAuthStore()
    authStore.setToken(
      {
        accessToken: 'old-access-token',
        idToken: '',
        refreshToken: 'old-refresh-token',
        expiresAt: Math.floor(Date.now() / 1000) + 3600,
      },
      { sub: 'old-user-sub' },
    )

    let resolveOriginal!: (response: Response) => void
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      if (String(input) === '/api/v1/state-changing') {
        return new Promise<Response>((resolve) => {
          resolveOriginal = resolve
        })
      }

      return Promise.resolve(makeResponse({ ok: true }) as unknown as Response)
    })

    const request = apiFetch('/api/v1/state-changing', { method: 'POST' })

    useOIDC().setToken(
      {
        accessToken: 'new-access-token',
        idToken: '',
        refreshToken: 'new-refresh-token',
        expiresAt: Math.floor(Date.now() / 1000) + 3600,
      },
      { sub: 'new-user-sub' },
    )
    resolveOriginal(makeResponse('Unauthorized', { status: 401, ok: false }) as unknown as Response)

    await expect(request).rejects.toThrow('Unauthorized')
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(authStore.token?.accessToken).toBe('new-access-token')
  })

  it('retries a 401 when the token rotated while the original request was pending', async () => {
    const authStore = useAuthStore()
    authStore.setToken(
      {
        accessToken: 'old-access-token',
        idToken: '',
        refreshToken: 'old-refresh-token',
        expiresAt: Math.floor(Date.now() / 1000) + 3600,
      },
      { sub: 'user-sub' },
    )

    let resolveOriginal!: (response: Response) => void
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input) === '/api/v1/state-changing' && vi.mocked(fetch).mock.calls.length === 1) {
        return new Promise<Response>((resolve) => {
          resolveOriginal = resolve
        })
      }
      const headers = init?.headers as Record<string, string>
      expect(headers.Authorization).toBe('Bearer rotated-access-token')
      return Promise.resolve(makeResponse({ ok: true }) as unknown as Response)
    })

    const request = apiFetch('/api/v1/state-changing', { method: 'POST' })

    authStore.setToken(
      {
        accessToken: 'rotated-access-token',
        idToken: '',
        refreshToken: 'rotated-refresh-token',
        expiresAt: Math.floor(Date.now() / 1000) + 3600,
      },
      { sub: 'user-sub' },
    )
    resolveOriginal(makeResponse('Unauthorized', { status: 401, ok: false }) as unknown as Response)

    await expect(request).resolves.toEqual({ ok: true })
    // The rotated bearer is reused directly; no second refresh is submitted.
    expect(fetch).toHaveBeenCalledTimes(2)
  })
})
