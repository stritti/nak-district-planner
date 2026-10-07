import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { submitRegistration } from './registrations'

describe('submitRegistration', () => {
  beforeEach(() => {
    document.cookie = 'csrf_token=signed-token; path=/'
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 201,
        headers: { get: () => null },
        json: () => Promise.resolve({ id: 'r1' }),
      }),
    )
  })

  afterEach(() => {
    document.cookie = 'csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/'
    vi.unstubAllGlobals()
  })

  it('sends the CSRF cookie value as header, the backend rejects cookie-only requests', async () => {
    await submitRegistration('d1', { name: 'A', email: 'a@example.org' } as never)

    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(url).toBe('/api/v1/districts/d1/registrations')
    expect(init?.method).toBe('POST')
    expect((init?.headers as Record<string, string>)['X-CSRF-Token']).toBe('signed-token')
  })
})
