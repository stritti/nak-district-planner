import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import * as districtApi from '../api/districts'
import { useAuthStore } from '../stores/auth'
import { useDistrictsStore } from '../stores/districts'
import DistrictContextSwitcher from './DistrictContextSwitcher.vue'

vi.mock('../api/districts')

const district = (id: string, name: string) => ({
  id, name, state_code: null, created_at: '', updated_at: '',
})

function setup(authenticated = true) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const auth = useAuthStore()
  if (authenticated) {
    auth.setToken(
      { accessToken: 'test', idToken: 'test', expiresAt: Date.now() / 1000 + 3600 },
      { sub: 'user-1' },
    )
  }
  const store = useDistrictsStore()
  const wrapper = mount(DistrictContextSwitcher, { global: { plugins: [pinia] } })
  return { wrapper, store, auth }
}

beforeEach(() => {
  vi.resetAllMocks()
  sessionStorage.clear()
})

describe('DistrictContextSwitcher', () => {
  it('does not request or display districts for anonymous users', async () => {
    const { wrapper } = setup(false)
    await flushPromises()
    expect(districtApi.listDistricts).not.toHaveBeenCalled()
    expect(wrapper.find('[data-testid="global-district-context"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('shows the one accessible district as read-only context', async () => {
    vi.mocked(districtApi.listDistricts).mockResolvedValue([district('d1', 'Tuttlingen')])
    const { wrapper, store } = setup()
    await flushPromises()
    expect(store.selectedDistrictId).toBe('d1')
    expect(wrapper.get('[data-testid="global-district-context"]').text()).toContain('Tuttlingen')
    expect(wrapper.get('[aria-label="Aktueller Bezirk: Tuttlingen"]').exists()).toBe(true)
    expect(wrapper.find('#global-district-select').exists()).toBe(false)
    wrapper.unmount()
  })

  it('offers only returned districts and updates the shared global selection', async () => {
    vi.mocked(districtApi.listDistricts).mockResolvedValue([
      district('d1', 'Tuttlingen'), district('d2', 'Konstanz'),
    ])
    const { wrapper, store } = setup()
    await flushPromises()
    const select = wrapper.get('#global-district-select')
    expect(select.findAll('option').map((option) => option.text())).toEqual(['Tuttlingen', 'Konstanz'])
    expect((select.element as HTMLSelectElement).value).toBe('d1')
    await select.setValue('d2')
    expect(store.selectedDistrictId).toBe('d2')
    expect((select.element as HTMLSelectElement).value).toBe('d2')
    wrapper.unmount()
  })

  it('restores a valid session selection and repairs a revoked one', async () => {
    sessionStorage.setItem('planner.view-settings.v1:' + JSON.stringify(['user-1', 'navigation', 'district']), JSON.stringify({ district: 'd2' }))
    vi.mocked(districtApi.listDistricts).mockResolvedValue([district('d1', 'Tuttlingen'), district('d2', 'Konstanz')])
    const { wrapper, store } = setup()
    await flushPromises()
    expect(store.selectedDistrictId).toBe('d2')
    vi.mocked(districtApi.listDistricts).mockResolvedValue([district('d1', 'Tuttlingen')])
    await store.fetchDistricts()
    expect(store.selectedDistrictId).toBe('d1')
    expect(wrapper.find('#global-district-select').exists()).toBe(false)
    wrapper.unmount()
  })

  it('shows no context for pending approval or an empty accessible list', async () => {
    vi.mocked(districtApi.listDistricts).mockResolvedValue([])
    const { wrapper, store } = setup()
    await flushPromises()
    expect(store.selectedDistrictId).toBe('')
    expect(wrapper.find('[data-testid="global-district-context"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('discards selected district and controls on logout and identity change', async () => {
    vi.mocked(districtApi.listDistricts).mockResolvedValue([district('d1', 'Tuttlingen')])
    const { wrapper, auth, store } = setup()
    await flushPromises()
    auth.clearAuth()
    await flushPromises()
    expect(store.selectedDistrictId).toBe('')
    expect(wrapper.find('[data-testid="global-district-context"]').exists()).toBe(false)
    vi.mocked(districtApi.listDistricts).mockResolvedValue([district('d2', 'Konstanz')])
    auth.setToken(
      { accessToken: 'test2', idToken: 'test2', expiresAt: Date.now() / 1000 + 3600 },
      { sub: 'user-2' },
    )
    await flushPromises()
    expect(store.selectedDistrictId).toBe('d2')
    wrapper.unmount()
  })

  it('does not expose stale context after an API failure', async () => {
    vi.mocked(districtApi.listDistricts).mockRejectedValue(new Error('offline'))
    const { wrapper, store } = setup()
    await flushPromises()
    expect(store.districts).toEqual([])
    expect(wrapper.find('[data-testid="global-district-context"]').exists()).toBe(false)
    wrapper.unmount()
  })
})
