// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { afterEach, describe, expect, it, vi } from 'vitest'
import { REFRESH_SESSION_COORDINATION_ID } from './oidcToken'
import { restoreRefreshSession } from './oidcSessionRestore'

function jwt(claims: object): string {
  const payload = btoa(JSON.stringify(claims)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '')
  return `header.${payload}.signature`
}

const originalFetch = globalThis.fetch

afterEach(() => {
  globalThis.fetch = originalFetch
  vi.restoreAllMocks()
})

describe('restoreRefreshSession', () => {
  it('bootstraps discovery before the CSRF-protected restore request', async () => {
    const ensureDiscovery = vi.fn().mockResolvedValue(undefined)
    const installSession = vi.fn()
    globalThis.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      access_token: 'access',
      id_token: jwt({ sub: 'user-1', email: 'user@example.org' }),
      expires_in: 900,
      refresh_session: true,
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }))

    const restored = await restoreRefreshSession({
      ensureDiscovery,
      fetchUserInfo: vi.fn(),
      installSession,
    })

    expect(restored).toBe(true)
    expect(ensureDiscovery).toHaveBeenCalledOnce()
    expect(ensureDiscovery.mock.invocationCallOrder[0]).toBeLessThan(
      vi.mocked(globalThis.fetch).mock.invocationCallOrder[0],
    )
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/v1/auth/oidc/token', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ grant_type: 'refresh_token' }),
    }))
    expect(installSession).toHaveBeenCalledWith(
      expect.objectContaining({
        accessToken: 'access',
        refreshToken: REFRESH_SESSION_COORDINATION_ID,
      }),
      expect.objectContaining({ sub: 'user-1' }),
    )
  })

  it('does not submit a cookie-backed POST when discovery bootstrap fails', async () => {
    const installSession = vi.fn()
    globalThis.fetch = vi.fn()

    expect(await restoreRefreshSession({
      ensureDiscovery: vi.fn().mockRejectedValue(new Error('discovery unavailable')),
      fetchUserInfo: vi.fn(),
      installSession,
    })).toBe(false)
    expect(globalThis.fetch).not.toHaveBeenCalled()
    expect(installSession).not.toHaveBeenCalled()
  })

  it('uses userinfo when token claims do not contain a subject', async () => {
    const installSession = vi.fn()
    const ensureDiscovery = vi.fn().mockResolvedValue(undefined)
    const fetchUserInfo = vi.fn().mockResolvedValue({ sub: 'userinfo-user' })
    globalThis.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      access_token: 'opaque-access',
      refresh_session: true,
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }))

    expect(await restoreRefreshSession({ ensureDiscovery, fetchUserInfo, installSession })).toBe(true)
    expect(ensureDiscovery).toHaveBeenCalledOnce()
    expect(fetchUserInfo).toHaveBeenCalledWith('opaque-access')
    expect(installSession).toHaveBeenCalledWith(
      expect.any(Object),
      expect.objectContaining({ sub: 'userinfo-user' }),
    )
  })

  it.each([
    new Response('', { status: 401 }),
    new Response(JSON.stringify({ access_token: 'access', refresh_session: false }), { status: 200 }),
    new Response('{not-json', { status: 200 }),
  ])('fails closed without installing a session for unusable responses', async (response) => {
    const installSession = vi.fn()
    globalThis.fetch = vi.fn().mockResolvedValue(response)

    expect(await restoreRefreshSession({
      ensureDiscovery: vi.fn().mockResolvedValue(undefined),
      fetchUserInfo: vi.fn(),
      installSession,
    })).toBe(false)
    expect(installSession).not.toHaveBeenCalled()
  })

  it('treats network failure as logged out', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new TypeError('offline'))

    expect(await restoreRefreshSession({
      ensureDiscovery: vi.fn().mockResolvedValue(undefined),
      fetchUserInfo: vi.fn(),
      installSession: vi.fn(),
    })).toBe(false)
  })
})
