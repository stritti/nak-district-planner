import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useBuildInfoStore } from './buildInfo'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status })
}

describe('buildInfo store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('exposes the build-time frontend version', () => {
    expect(useBuildInfoStore().frontendVersion).toBe('0.0.0-test')
  })

  it('reads the backend version from the public health endpoint without credentials', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ status: 'ok', version: '1.0.0-rc.4' }))
    vi.stubGlobal('fetch', fetchMock)
    const store = useBuildInfoStore()

    await store.load()

    expect(store.backendVersion).toBe('1.0.0-rc.4')
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/health')
    expect(init.headers).not.toHaveProperty('Authorization')
  })

  it('still reports the version of a degraded backend (503)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ status: 'degraded', version: '1.0.0-rc.4' }, 503)))
    const store = useBuildInfoStore()

    await store.load()

    expect(store.backendVersion).toBe('1.0.0-rc.4')
  })

  it.each([
    ['a missing version', jsonResponse({ status: 'ok' })],
    ['a non-string version', jsonResponse({ version: 4 })],
    ['an empty version', jsonResponse({ version: '' })],
    ['a null body', jsonResponse(null)],
    ['a non-JSON body', new Response('<html>Bad Gateway</html>', { status: 502 })],
  ])('shows no backend version for %s', async (_label, response) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response))
    const store = useBuildInfoStore()
    store.backendVersion = '9.9.9'

    await store.load()

    expect(store.backendVersion).toBeNull()
  })

  it('shows no backend version when the request fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    const store = useBuildInfoStore()

    await expect(store.load()).resolves.toBeUndefined()

    expect(store.backendVersion).toBeNull()
  })
})
