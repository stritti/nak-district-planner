// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '../stores/auth'

const mocks = vi.hoisted(() => ({
  routeQuery: {} as Record<string, unknown>,
  push: vi.fn(),
  exchangeCodeForToken: vi.fn(),
  token: { value: null as null | Record<string, unknown> },
  user: { value: null as null | Record<string, unknown> },
}))

vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue-router')>()
  return {
    ...actual,
    useRouter: () => ({ push: mocks.push }),
    useRoute: () => ({ query: mocks.routeQuery }),
  }
})
vi.mock('../composables/useOIDC', () => ({
  useOIDC: () => ({
    exchangeCodeForToken: mocks.exchangeCodeForToken,
    token: mocks.token,
    user: mocks.user,
  }),
}))

import AuthCallbackView from './AuthCallbackView.vue'

function mountView() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const auth = useAuthStore()
  auth.refreshCurrentUserFlags = vi.fn().mockResolvedValue(undefined)
  return { wrapper: mount(AuthCallbackView, { global: { plugins: [pinia] } }), auth }
}

describe('AuthCallbackView', () => {
  beforeEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
    Object.keys(mocks.routeQuery).forEach((key) => delete mocks.routeQuery[key])
    mocks.token.value = null
    mocks.user.value = null
    mocks.exchangeCodeForToken.mockResolvedValue(undefined)
    sessionStorage.clear()
  })

  it('shows an upstream provider error and description without exchanging a code', async () => {
    mocks.routeQuery.error = 'access_denied'
    mocks.routeQuery.error_description = 'User cancelled'
    const { wrapper } = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('access_denied: User cancelled')
    expect(mocks.exchangeCodeForToken).not.toHaveBeenCalled()
  })

  it('handles a provider error without a description', async () => {
    mocks.routeQuery.error = 'login_required'
    const { wrapper } = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('login_required')
  })

  it('rejects callbacks without an authorization code', async () => {
    const { wrapper } = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('Kein Autorisierungscode')
  })

  it('rejects a mismatching state before token exchange', async () => {
    mocks.routeQuery.code = 'code-1'
    mocks.routeQuery.state = 'received-state'
    sessionStorage.setItem('oidc_state', 'expected-state')
    const { wrapper } = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('State-Parameter stimmt nicht überein')
    expect(mocks.exchangeCodeForToken).not.toHaveBeenCalled()
  })

  it('reports an incomplete token exchange', async () => {
    mocks.routeQuery.code = 'code-1'
    mocks.routeQuery.state = 'state-1'
    sessionStorage.setItem('oidc_state', 'state-1')
    const { wrapper } = mountView()
    await flushPromises()

    expect(mocks.exchangeCodeForToken).toHaveBeenCalledWith('code-1')
    expect(wrapper.text()).toContain('Token-Austausch fehlgeschlagen')
  })

  it('refreshes access flags and redirects after a successful callback', async () => {
    vi.useFakeTimers()
    mocks.routeQuery.code = 'code-1'
    mocks.routeQuery.state = 'state-1'
    sessionStorage.setItem('oidc_state', 'state-1')
    mocks.exchangeCodeForToken.mockImplementation(async () => {
      mocks.token.value = { accessToken: 'access' }
      mocks.user.value = { sub: 'user-1' }
    })
    const { wrapper, auth } = mountView()

    await vi.advanceTimersByTimeAsync(500)
    await flushPromises()

    expect(auth.refreshCurrentUserFlags).toHaveBeenCalledOnce()
    expect(mocks.push).toHaveBeenCalledWith('/events')
    expect(wrapper.text()).toContain('Erfolgreich angemeldet')
  })

  it('shows token exchange exceptions and offers navigation back to login', async () => {
    mocks.routeQuery.code = 'code-1'
    mocks.routeQuery.state = 'state-1'
    sessionStorage.setItem('oidc_state', 'state-1')
    mocks.exchangeCodeForToken.mockRejectedValue(new Error('Token endpoint offline'))
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const { wrapper } = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('Token endpoint offline')
    await wrapper.get('button').trigger('click')
    expect(mocks.push).toHaveBeenCalledWith('/login')
  })
})
