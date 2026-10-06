import { afterEach, describe, expect, it } from 'vitest'
import { getCookie, getCurrentCSRFHeaders } from './useCSRF'

function expireCookie(name: string): void {
  document.cookie = `${name}=; Max-Age=0; Path=/`
}

describe('CSRF request helpers', () => {
  afterEach(() => {
    expireCookie('csrf_token')
    expireCookie('custom_csrf')
  })

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
