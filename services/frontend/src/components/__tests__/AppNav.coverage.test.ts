import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import AppNav from '@/components/AppNav.vue'
import { useAuthStore } from '@/stores/auth'
import { useDistrictsStore } from '@/stores/districts'
import { useNotificationStore } from '@/stores/notifications'

const mocks = vi.hoisted(() => ({
  logout: vi.fn().mockResolvedValue(undefined),
  toggle: vi.fn(),
}))

vi.mock('@/composables/useOIDC', () => ({
  useOIDC: () => ({ initialize: vi.fn(), logout: mocks.logout }),
}))

vi.mock('@/composables/useDarkMode', () => ({
  useDarkMode: () => ({ isDark: { value: false }, toggle: mocks.toggle }),
}))

const candidateId = '123e4567-e89b-12d3-a456-426614174000'
const NotificationBellStub = defineComponent({
  emits: ['notification-click'],
  setup(_, { emit }) {
    return () => h('button', {
      'data-test': 'notification',
      onClick: () => emit('notification-click', {
        type: 'CANDIDATE_REVIEW',
        payload: { candidate_id: candidateId },
      }),
    }, 'notification')
  },
})

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/events', component: { template: '<div />' } },
      { path: '/matrix', component: { template: '<div />' } },
      { path: '/admin/districts', component: { template: '<div />' } },
      { path: '/admin/leaders', component: { template: '<div />' } },
      { path: '/admin/calendars', component: { template: '<div />' } },
      { path: '/admin/external-candidates', component: { template: '<div />' } },
      { path: '/admin/export', component: { template: '<div />' } },
      { path: '/login', component: { template: '<div />' } },
    ],
  })
}

async function setup(authenticated: boolean, districtId = '') {
  const pinia = createPinia()
  setActivePinia(pinia)
  const authStore = useAuthStore()
  const districtStore = useDistrictsStore()
  const notificationStore = useNotificationStore()
  const router = makeRouter()
  await router.push('/events')
  await router.isReady()

  if (authenticated) {
    authStore.setToken({ accessToken: 'token', idToken: 'id', expiresAt: Date.now() / 1000 + 3600 })
    authStore.user = { email: 'user@example.org', name: 'User' } as typeof authStore.user
  }
  districtStore.selectedDistrictId = districtId

  const startPolling = vi.spyOn(notificationStore, 'startPolling').mockImplementation(() => undefined)
  const reset = vi.spyOn(notificationStore, 'reset').mockImplementation(() => undefined)
  const stopPolling = vi.spyOn(notificationStore, 'stopPolling').mockImplementation(() => undefined)
  const clearAuth = vi.spyOn(authStore, 'clearAuth')

  const wrapper = mount(AppNav, {
    global: {
      plugins: [pinia, router],
      stubs: { NotificationBell: NotificationBellStub },
    },
  })
  await flushPromises()
  return { wrapper, router, authStore, districtStore, startPolling, reset, stopPolling, clearAuth }
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('AppNav coverage gaps', () => {
  it('polls for the selected district and routes notification clicks to review', async () => {
    const { wrapper, router, startPolling } = await setup(true, 'd1')

    expect(startPolling).toHaveBeenCalledWith('d1')
    await wrapper.get('[data-test="notification"]').trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/admin/external-candidates')
    expect(router.currentRoute.value.query.candidate_id).toBe(candidateId)
  })

  it('resets notifications when unauthenticated and toggles dark mode', async () => {
    const { wrapper, reset } = await setup(false)

    expect(reset).toHaveBeenCalled()
    expect(wrapper.text()).toContain('Anmelden')
    await wrapper.get('button[title="Light Mode aktivieren"]').trigger('click')
    expect(mocks.toggle).toHaveBeenCalledTimes(1)
  })

  it('logs out, clears navigation state and stops polling on unmount', async () => {
    const { wrapper, router, reset, stopPolling, clearAuth } = await setup(true, 'd1')

    const userButton = wrapper.findAll('button').find((button) => button.text().includes('User'))!
    await userButton.trigger('click')
    const logoutButton = wrapper.findAll('button').find((button) => button.text().includes('Abmelden'))!
    await logoutButton.trigger('click')
    await flushPromises()

    expect(reset).toHaveBeenCalled()
    expect(mocks.logout).toHaveBeenCalledTimes(1)
    expect(clearAuth).toHaveBeenCalledTimes(1)
    expect(router.currentRoute.value.path).toBe('/login')

    wrapper.unmount()
    expect(stopPolling).toHaveBeenCalled()
  })
})
