import { describe, it, expect, vi, beforeEach } from 'vitest'
import { apiFetch } from './client'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '../stores/auth'

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
    vi.stubGlobal('fetch', vi.fn())
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
})
