import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useVersionStore } from './version'
import * as systemApi from '@/api/system'

vi.mock('@/api/system', () => ({
  getVersion: vi.fn(),
  triggerUpdate: vi.fn(),
}))

const versionResponse = (overrides = {}) => ({
  current_version: '0.4.5',
  latest_version: '0.5.0',
  update_available: true,
  last_checked: 123,
  release_url: 'https://example.test/releases/0.5.0',
  ...overrides,
})

describe('useVersionStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('starts with idle state and no version', () => {
    const store = useVersionStore()
    expect(store.currentVersion).toBe('')
    expect(store.latestVersion).toBeNull()
    expect(store.loading).toBe(false)
    expect(store.hasUpdate).toBe(false)
  })

  it('loads version metadata and forwards refresh', async () => {
    vi.mocked(systemApi.getVersion).mockResolvedValue(versionResponse())
    const store = useVersionStore()

    await store.checkVersion(true)

    expect(systemApi.getVersion).toHaveBeenCalledWith(true)
    expect(store.currentVersion).toBe('0.4.5')
    expect(store.latestVersion).toBe('0.5.0')
    expect(store.lastChecked).toBe(123)
    expect(store.releaseUrl).toContain('/0.5.0')
    expect(store.hasUpdate).toBe(true)
    expect(store.loading).toBe(false)
  })

  it('clears hasUpdate when versions match or no latest version exists', async () => {
    const store = useVersionStore()
    store.hasUpdate = true
    vi.mocked(systemApi.getVersion).mockResolvedValueOnce(
      versionResponse({ current_version: '0.5.0', latest_version: '0.5.0' }),
    )
    await store.checkVersion()
    expect(store.hasUpdate).toBe(false)

    store.hasUpdate = true
    vi.mocked(systemApi.getVersion).mockResolvedValueOnce(
      versionResponse({ latest_version: null }),
    )
    await store.checkVersion()
    expect(store.hasUpdate).toBe(false)
  })

  it('handles version lookup errors silently', async () => {
    vi.mocked(systemApi.getVersion).mockRejectedValue(new Error('Network error'))
    const store = useVersionStore()
    store.hasUpdate = true

    await store.checkVersion()

    expect(store.loading).toBe(false)
    expect(store.hasUpdate).toBe(false)
  })

  it('dismisses a known latest version and ignores dismiss without one', async () => {
    const store = useVersionStore()
    store.dismiss()
    expect(localStorage.getItem('dismissedVersion')).toBeNull()

    vi.mocked(systemApi.getVersion).mockResolvedValue(versionResponse())
    await store.checkVersion()
    store.dismiss()

    expect(store.dismissedVersion).toBe('0.5.0')
    expect(localStorage.getItem('dismissedVersion')).toBe('0.5.0')
    expect(store.hasUpdate).toBe(false)
  })

  it('respects a dismissed version and re-shows a newer version', async () => {
    vi.mocked(systemApi.getVersion)
      .mockResolvedValueOnce(versionResponse())
      .mockResolvedValueOnce(versionResponse())
      .mockResolvedValueOnce(versionResponse({ latest_version: '0.6.0' }))

    const store = useVersionStore()
    await store.checkVersion()
    store.dismiss()
    await store.checkVersion()
    expect(store.hasUpdate).toBe(false)

    await store.checkVersion()
    expect(store.hasUpdate).toBe(true)
  })

  it('triggers an update and records a successful result and mode', async () => {
    const result = {
      status: 'started' as const,
      mode: 'docker-socket' as const,
      instructions: null,
    }
    vi.mocked(systemApi.triggerUpdate).mockResolvedValue(result)
    const store = useVersionStore()

    await expect(store.trigger()).resolves.toEqual(result)

    expect(store.updateResult).toEqual(result)
    expect(store.updateMode).toBe('docker-socket')
    expect(store.updating).toBe(false)
  })

  it('records a safe manual result and rethrows when update triggering fails', async () => {
    const error = new Error('update unavailable')
    vi.mocked(systemApi.triggerUpdate).mockRejectedValue(error)
    const store = useVersionStore()

    await expect(store.trigger()).rejects.toThrow('update unavailable')

    expect(store.updateResult).toEqual({
      status: 'error',
      mode: 'manual',
      instructions: null,
    })
    expect(store.updating).toBe(false)
  })

  it('resets mutable version state', async () => {
    vi.mocked(systemApi.getVersion).mockResolvedValue(versionResponse())
    const store = useVersionStore()
    await store.checkVersion()
    store.updateResult = { status: 'manual', mode: 'manual', instructions: 'run it' }

    store.$reset()

    expect(store.currentVersion).toBe('')
    expect(store.latestVersion).toBeNull()
    expect(store.lastChecked).toBeNull()
    expect(store.releaseUrl).toBeNull()
    expect(store.hasUpdate).toBe(false)
    expect(store.updateResult).toBeNull()
  })
})
