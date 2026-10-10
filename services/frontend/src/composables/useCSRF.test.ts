// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { afterEach, describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'
import { getCookie, getCurrentCSRFHeaders, useCSRF } from './useCSRF'

function expireCookie(name: string): void {
  document.cookie = `${name}=; Max-Age=0; Path=/`
}

afterEach(() => {
  expireCookie('csrf_token')
  expireCookie('custom_csrf')
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

describe('CSRF request helpers', () => {
  it('reads the current middleware cookie into the default request header', () => {
    document.cookie = 'csrf_token=current-token; Path=/'

    expect(getCookie('csrf_token')).toBe('current-token')
    expect(getCurrentCSRFHeaders()).toEqual({ 'X-CSRF-Token': 'current-token' })
  })

  it('returns no security header when the CSRF cookie is absent', () => {
    expireCookie('csrf_token')

    expect(getCurrentCSRFHeaders()).toEqual({})
  })

  it('supports explicit cookie and header names', () => {
    document.cookie = 'custom_csrf=custom-token; Path=/'

    expect(getCurrentCSRFHeaders({
      cookieName: 'custom_csrf',
      headerName: 'X-Custom-CSRF',
    })).toEqual({ 'X-Custom-CSRF': 'custom-token' })
  })
})

describe('useCSRF', () => {
  it('loads the default cookie on mount and exposes the current request header', () => {
    document.cookie = 'csrf_token=token-123; Path=/'

    const { csrf } = mountHarness()

    expect(csrf.hasCSRFToken()).toBe(true)
    expect(csrf.getToken()).toBe('token-123')
    expect(csrf.getCSRFHeaders()).toEqual({ 'X-CSRF-Token': 'token-123' })
  })

  it('supports custom cookie/header names and explicit reloads', () => {
    const { csrf } = mountHarness({ cookieName: 'custom_csrf', headerName: 'X-Custom-CSRF' })
    expect(csrf.hasCSRFToken()).toBe(false)
    expect(csrf.getCSRFHeaders()).toEqual({})

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

  it('picks up middleware token rotation after mount', () => {
    document.cookie = 'csrf_token=initial; Path=/'
    const { csrf } = mountHarness()

    document.cookie = 'csrf_token=rotated; Path=/'

    expect(csrf.getCSRFHeaders()).toEqual({ 'X-CSRF-Token': 'rotated' })
    expect(csrf.csrfToken.value).toBe('rotated')
  })
})
