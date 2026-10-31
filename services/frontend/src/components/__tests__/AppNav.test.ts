// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import AppNav from '@/components/AppNav.vue'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/composables/useOIDC', () => ({
  useOIDC: () => ({
    initialize: vi.fn(),
    logout: vi.fn().mockResolvedValue(undefined),
  }),
}))

vi.mock('@/composables/useDarkMode', () => ({
  useDarkMode: () => ({ isDark: { value: false }, toggle: vi.fn() }),
}))

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/events', name: 'events', component: { template: '<div />' } },
      { path: '/matrix', name: 'matrix', component: { template: '<div />' } },
      { path: '/admin/districts', component: { template: '<div />' } },
      { path: '/admin/leaders', component: { template: '<div />' } },
      { path: '/admin/calendars', component: { template: '<div />' } },
      { path: '/admin/export', component: { template: '<div />' } },
      { path: '/admin/users', component: { template: '<div />' } },
      { path: '/login', component: { template: '<div />' } },
    ],
  })
}

describe('AppNav mobile menu', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('shows superadmin badge and pending registrations inside the mobile menu', async () => {
    const router = makeRouter()
    await router.push('/events')
    await router.isReady()

    const authStore = useAuthStore()
    authStore.setToken({ accessToken: 'x', idToken: 'x', expiresAt: Date.now() / 1000 + 3600 })
    authStore.isSuperadmin = true
    authStore.pendingRegistrationsCount = 2

    const wrapper = mount(AppNav, { global: { plugins: [router] } })

    await wrapper.find('button[aria-label="Navigation öffnen"]').trigger('click')

    expect(wrapper.text()).toContain('Superadmin')
    expect(wrapper.text()).toContain('Registrierungen offen')
    expect(wrapper.text()).toContain('2')
  })

  it('closes the mobile menu after navigating to a different route', async () => {
    const router = makeRouter()
    await router.push('/events')
    await router.isReady()

    const authStore = useAuthStore()
    authStore.setToken({ accessToken: 'x', idToken: 'x', expiresAt: Date.now() / 1000 + 3600 })

    const wrapper = mount(AppNav, { global: { plugins: [router] } })

    await wrapper.find('button[aria-label="Navigation öffnen"]').trigger('click')
    expect(wrapper.find('button[aria-label="Navigation schließen"]').exists()).toBe(true)

    await router.push('/matrix')
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    expect(wrapper.find('button[aria-label="Navigation schließen"]').exists()).toBe(false)
  })

  it.each([
    ['a planner', [{ role: 'PLANNER', scope_type: 'DISTRICT' as const, scope_id: 'd1' }], false, false],
    ['a congregation admin', [{ role: 'CONGREGATION_ADMIN', scope_type: 'CONGREGATION' as const, scope_id: 'c1' }], false, true],
    ['a superadmin without memberships', [], true, true],
  ])('shows the user administration link to %s only when it manages a unit', async (_who, memberships, superadmin, visible) => {
    const router = makeRouter()
    await router.push('/events')
    await router.isReady()

    const authStore = useAuthStore()
    authStore.setToken({ accessToken: 'x', idToken: 'x', expiresAt: Date.now() / 1000 + 3600 })
    authStore.memberships = memberships
    authStore.isSuperadmin = superadmin

    const wrapper = mount(AppNav, { global: { plugins: [router] } })

    expect(wrapper.find('a[href="/admin/users"]').exists()).toBe(visible)
  })

  it.each([
    ['a viewer', [{ role: 'VIEWER', scope_type: 'DISTRICT' as const, scope_id: 'd1' }], false, false],
    ['a planner', [{ role: 'PLANNER', scope_type: 'DISTRICT' as const, scope_id: 'd1' }], false, true],
    ['a superadmin without memberships', [], true, true],
  ])('shows the getting-started link to %s only when it plans a district', async (_who, memberships, superadmin, visible) => {
    const router = makeRouter()
    await router.push('/events')
    await router.isReady()

    const authStore = useAuthStore()
    authStore.setToken({ accessToken: 'x', idToken: 'x', expiresAt: Date.now() / 1000 + 3600 })
    authStore.memberships = memberships
    authStore.isSuperadmin = superadmin

    const wrapper = mount(AppNav, { global: { plugins: [router] } })

    expect(wrapper.findAll('a[href="/"]').some((link) => link.text().includes('Erste Schritte'))).toBe(visible)
  })
})
