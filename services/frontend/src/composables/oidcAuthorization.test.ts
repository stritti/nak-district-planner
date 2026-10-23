// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getAuthorizationUrl, type AuthorizationDeps } from './oidcAuthorization'

function deps(overrides: Partial<AuthorizationDeps> = {}): AuthorizationDeps {
  return {
    config: { redirectUri: 'https://app.example/auth/callback', scope: 'openid profile email' } as AuthorizationDeps['config'],
    getClientId: () => 'nak-planner-frontend',
    getDiscovery: () => ({ authorization_endpoint: 'https://auth.example/realms/nak/auth' }) as never,
    loadDiscovery: vi.fn().mockResolvedValue(undefined),
    fetchUserInfo: vi.fn(),
    onSessionInstalled: vi.fn(),
    ...overrides,
  }
}

beforeEach(() => sessionStorage.clear())

describe('getAuthorizationUrl', () => {
  it('builds a PKCE authorization request without a prompt by default', async () => {
    const url = new URL(await getAuthorizationUrl(deps()))

    expect(`${url.origin}${url.pathname}`).toBe('https://auth.example/realms/nak/auth')
    expect(url.searchParams.get('client_id')).toBe('nak-planner-frontend')
    expect(url.searchParams.get('response_type')).toBe('code')
    expect(url.searchParams.get('code_challenge_method')).toBe('S256')
    expect(url.searchParams.has('prompt')).toBe(false)
  })

  it('asks for the registration form with prompt=create', async () => {
    const url = new URL(await getAuthorizationUrl(deps(), { prompt: 'create' }))

    expect(url.searchParams.get('prompt')).toBe('create')
    // The rest of the request is the same PKCE login, so the callback works unchanged.
    expect(url.searchParams.get('redirect_uri')).toBe('https://app.example/auth/callback')
    expect(url.searchParams.get('code_challenge')).toBeTruthy()
    expect(url.searchParams.get('state')).toBeTruthy()
  })

  it('fails without discovery', async () => {
    await expect(getAuthorizationUrl(deps({ getDiscovery: () => null }))).rejects.toThrow('Discovery not loaded')
  })
})
