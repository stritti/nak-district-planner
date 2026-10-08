import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import UpdateBanner from '@/components/UpdateBanner.vue'
import { useAuthStore } from '@/stores/auth'
import { useVersionStore } from '@/stores/version'
import * as systemApi from '@/api/system'

vi.mock('@/api/system', () => ({
  getVersion: vi.fn(),
  triggerUpdate: vi.fn(),
}))

function authenticate() {
  const auth = useAuthStore()
  auth.setToken(
    { accessToken: 'access', idToken: 'id', expiresAt: Math.floor(Date.now() / 1000) + 3600 },
    { sub: 'admin' },
  )
  return auth
}

function makeUpdateVisible(mode: 'manual' | 'docker-socket' = 'manual') {
  const store = useVersionStore()
  store.currentVersion = '0.4.5'
  store.latestVersion = '0.5.0'
  store.releaseUrl = 'https://example.test/releases/0.5.0'
  store.updateMode = mode
  store.hasUpdate = true
  return store
}

describe('UpdateBanner', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    localStorage.clear()
    vi.mocked(systemApi.getVersion).mockResolvedValue({
      current_version: '0.5.0',
      latest_version: '0.5.0',
      update_available: false,
      last_checked: 1,
      release_url: null,
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('stays hidden when the user is unauthenticated or no update exists', async () => {
    const wrapper = mount(UpdateBanner)
    await flushPromises()
    expect(wrapper.find('[data-testid="update-banner"]').exists()).toBe(false)

    authenticate()
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="update-banner"]').exists()).toBe(false)
  })

  it('shows version metadata, release notes and manual instructions', async () => {
    authenticate()
    const store = makeUpdateVisible('manual')
    vi.spyOn(store, 'checkVersion').mockResolvedValue(undefined)
    const wrapper = mount(UpdateBanner)
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Neue Version 0.5.0 verfügbar')
    expect(wrapper.text()).toContain('(aktuell: 0.4.5)')
    const release = wrapper.get('a')
    expect(release.attributes('href')).toBe('https://example.test/releases/0.5.0')
    expect(release.attributes('rel')).toBe('noopener noreferrer')

    await wrapper.findAll('button').find((button) => button.text().includes('Manuelle Anleitung'))!.trigger('click')
    expect(wrapper.text()).toContain('docker compose pull')
    expect(wrapper.text()).toContain('docker compose up -d')

    await wrapper.findAll('button').find((button) => button.text().includes('Manuelle Anleitung'))!.trigger('click')
    expect(wrapper.text()).not.toContain('SSH auf dem Server ausführen:')
  })

  it('dismisses the available update', async () => {
    authenticate()
    const store = makeUpdateVisible()
    vi.spyOn(store, 'checkVersion').mockResolvedValue(undefined)
    const wrapper = mount(UpdateBanner)
    await wrapper.vm.$nextTick()

    await wrapper.get('[data-testid="dismiss-update"]').trigger('click')

    expect(store.hasUpdate).toBe(false)
    expect(localStorage.getItem('dismissedVersion')).toBe('0.5.0')
    expect(wrapper.find('[data-testid="update-banner"]').exists()).toBe(false)
  })

  it('triggers docker-socket updates and renders success feedback', async () => {
    authenticate()
    const store = makeUpdateVisible('docker-socket')
    vi.spyOn(store, 'checkVersion').mockResolvedValue(undefined)
    vi.spyOn(store, 'trigger').mockResolvedValue({
      status: 'started',
      mode: 'docker-socket',
      instructions: null,
    })
    const wrapper = mount(UpdateBanner)
    await wrapper.vm.$nextTick()

    await wrapper.findAll('button').find((button) => button.text() === 'Aktualisieren')!.trigger('click')
    await flushPromises()

    expect(store.trigger).toHaveBeenCalledOnce()
    expect(wrapper.text()).toContain('Update gestartet')
    expect(wrapper.text()).toContain('Docker-Images werden aktualisiert')
  })

  it('opens manual instructions when trigger reports manual mode', async () => {
    authenticate()
    const store = makeUpdateVisible('docker-socket')
    vi.spyOn(store, 'checkVersion').mockResolvedValue(undefined)
    vi.spyOn(store, 'trigger').mockResolvedValue({
      status: 'manual',
      mode: 'manual',
      instructions: 'manual',
    })
    const wrapper = mount(UpdateBanner)
    await wrapper.vm.$nextTick()

    await wrapper.findAll('button').find((button) => button.text() === 'Aktualisieren')!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('SSH auf dem Server ausführen:')
  })

  it('renders error feedback when update triggering fails', async () => {
    authenticate()
    const store = makeUpdateVisible('docker-socket')
    vi.spyOn(store, 'checkVersion').mockResolvedValue(undefined)
    vi.spyOn(store, 'trigger').mockRejectedValue(new Error('boom'))
    const wrapper = mount(UpdateBanner)
    await wrapper.vm.$nextTick()

    await wrapper.findAll('button').find((button) => button.text() === 'Aktualisieren')!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Update fehlgeschlagen')
    expect(wrapper.text()).toContain('manuelle Anleitung')
  })

  it('checks on mount, polls every 30 minutes and clears the timer on unmount', async () => {
    vi.useFakeTimers()
    const store = useVersionStore()
    const checkVersion = vi.spyOn(store, 'checkVersion').mockResolvedValue(undefined)
    const clearIntervalSpy = vi.spyOn(globalThis, 'clearInterval')

    const wrapper = mount(UpdateBanner)
    expect(checkVersion).toHaveBeenCalledOnce()

    vi.advanceTimersByTime(30 * 60 * 1000)
    expect(checkVersion).toHaveBeenCalledTimes(2)

    wrapper.unmount()
    expect(clearIntervalSpy).toHaveBeenCalled()
  })
})
