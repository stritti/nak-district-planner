import { afterEach, describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'
import { useCSRF } from './useCSRF'

afterEach(() => {
  document.cookie = 'csrf_token=; Max-Age=0; Path=/'
  document.cookie = 'custom_csrf=; Max-Age=0; Path=/'
})

function mountHarness(config?: Parameters<typeof useCSRF>[0]) {
  let csrf!: ReturnType<typeof useCSRF>
  const Harness = defineComponent({
    setup() {
      csrf = useCSRF(config)
      return () => h('div')
    },
  })
  const wrapper = mount(Harness)
  return { wrapper, csrf }
}

describe('useCSRF', () => {
  it('loads the default cookie on mount and exposes the request header', () => {
    document.cookie = 'csrf_token=token-123; Path=/'

    const { csrf } = mountHarness()

    expect(csrf.hasCSRFToken()).toBe(true)
    expect(csrf.getToken()).toBe('token-123')
    expect(csrf.getCSRFHeaders()).toEqual({ 'X-CSRF-Token': 'token-123' })
  })

  it('supports custom cookie/header names and explicit reloads', () => {
    const { csrf } = mountHarness({ cookieName: 'custom_csrf', headerName: 'X-Custom-CSRF' })
    expect(csrf.hasCSRFToken()).toBe(false)
    expect(csrf.getCSRFHeaders()).toEqual({ 'X-Custom-CSRF': '' })

    document.cookie = 'custom_csrf=custom-token; Path=/'
    csrf.loadCSRFToken()

    expect(csrf.getToken()).toBe('custom-token')
    expect(csrf.getCSRFHeaders()).toEqual({ 'X-Custom-CSRF': 'custom-token' })
  })

  it('treats a missing cookie as an empty token', () => {
    const { csrf } = mountHarness()

    csrf.loadCSRFToken()

    expect(csrf.getToken()).toBe('')
    expect(csrf.hasCSRFToken()).toBe(false)
  })
})
