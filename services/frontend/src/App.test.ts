import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

const { initialize } = vi.hoisted(() => ({ initialize: vi.fn() }))
vi.mock('./composables/useOIDC', () => ({
  useOIDC: () => ({ initialize }),
}))

import App from './App.vue'
import { useAuthStore } from './stores/auth'

function createTestRouter(): Router {
  const component = { template: '<div data-test="route-view">route</div>' }
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/events', name: 'events', component },
      { path: '/matrix', name: 'matrix', component },
      { path: '/other', name: 'other', component },
    ],
  })
}

async function mountAt(path: string) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = createTestRouter()
  await router.push(path)
  await router.isReady()
  const wrapper = mount(App, {
    global: {
      plugins: [pinia, router],
      stubs: {
        AppNav: { template: '<nav data-test="app-nav" />' },
        UpdateBanner: { template: '<div data-test="update-banner" />' },
        ToastContainer: { template: '<div data-test="toasts" />' },
        ConfirmHost: { template: '<div data-test="confirm-host" />' },
        ContextualHelp: {
          props: ['context'],
          template: '<aside data-test="contextual-help">{{ context }}</aside>',
        },
      },
    },
  })
  return { wrapper, router, auth: useAuthStore(pinia) }
}

describe('App', () => {
  beforeEach(() => {
    initialize.mockClear()
  })

  it('initializes OIDC and uses the normal layout on event routes', async () => {
    const { wrapper } = await mountAt('/events')

    expect(initialize).toHaveBeenCalledOnce()
    expect(wrapper.get('main').classes()).toContain('max-w-7xl')
    expect(wrapper.get('[data-test="contextual-help"]').text()).toBe('events')
    expect(wrapper.find('[data-test="route-view"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="app-nav"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="toasts"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="confirm-host"]').exists()).toBe(true)
  })

  it('uses the wide matrix layout and hides contextual help outside events', async () => {
    const { wrapper, router } = await mountAt('/matrix')

    expect(wrapper.get('main').classes()).toContain('w-full')
    expect(wrapper.find('[data-test="contextual-help"]').exists()).toBe(false)

    await router.push('/other')
    await wrapper.vm.$nextTick()
    expect(wrapper.get('main').classes()).toContain('max-w-7xl')
  })

  it('shows pending approval only for authenticated pending users', async () => {
    const { wrapper, auth } = await mountAt('/events')
    expect(wrapper.text()).not.toContain('Freigabe ausstehend')

    auth.setToken(
      { accessToken: 'access', idToken: 'id', expiresAt: Math.floor(Date.now() / 1000) + 3600 },
      { sub: 'user' },
    )
    auth.accessStatus = 'PENDING_APPROVAL'
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Freigabe ausstehend')

    auth.accessStatus = 'ACTIVE'
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).not.toContain('Freigabe ausstehend')
  })
})
