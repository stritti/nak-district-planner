import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const loadDiscovery = vi.fn()
const getAuthorizationUrl = vi.fn()
const push = vi.fn()

vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue-router')>()
  return {
    ...actual,
    useRouter: () => ({ push }),
  }
})
vi.mock('../composables/useOIDC', () => ({
  useOIDC: () => ({ loadDiscovery, getAuthorizationUrl }),
}))

import LoginView from './LoginView.vue'

function mountView() {
  return mount(LoginView, {
    global: {
      stubs: {
        RouterLink: { template: '<a><slot /></a>' },
        ContextualHelp: true,
      },
    },
  })
}

describe('LoginView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    loadDiscovery.mockResolvedValue(undefined)
    getAuthorizationUrl.mockResolvedValue('https://idp.example/authorize')
  })

  it('loads discovery on startup and renders the login action', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(loadDiscovery).toHaveBeenCalledOnce()
    expect(wrapper.text()).toContain('Mit Single Sign-on anmelden')
    expect(wrapper.text()).not.toContain('Discovery wird geladen')
  })

  it('shows the loading state while discovery is pending', async () => {
    let resolve!: () => void
    loadDiscovery.mockReturnValue(new Promise<void>((done) => { resolve = done }))
    const wrapper = mountView()
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Discovery wird geladen')
    resolve()
    await flushPromises()
    expect(wrapper.text()).toContain('Mit Single Sign-on anmelden')
  })

  it('shows a friendly error when discovery fails', async () => {
    loadDiscovery.mockRejectedValue(new Error('provider offline'))
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('OIDC Discovery fehlgeschlagen')
    expect(consoleSpy).toHaveBeenCalled()
  })

  it('requests an authorization URL on form submit', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(getAuthorizationUrl).toHaveBeenCalledOnce()
  })

  it('surfaces authorization failures and resets loading', async () => {
    getAuthorizationUrl.mockRejectedValue(new Error('Login nicht verfügbar'))
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const wrapper = mountView()
    await flushPromises()

    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('Login nicht verfügbar')
    expect(wrapper.text()).toContain('Mit Single Sign-on anmelden')
  })
})
