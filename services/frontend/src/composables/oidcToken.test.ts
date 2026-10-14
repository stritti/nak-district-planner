// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  REFRESH_SESSION_COORDINATION_ID,
  identityFromTokenExchange,
  isValidTokenExchangeResponse,
  isValidTokenShape,
} from './oidcToken'
import type { OIDCToken, OIDCUser } from './oidcTypes'

const currentToken: OIDCToken = {
  accessToken: 'old-access',
  idToken: 'old-id',
  refreshToken: REFRESH_SESSION_COORDINATION_ID,
  expiresAt: 1,
}

const currentUser: OIDCUser = {
  sub: 'current-user',
  email: 'current@example.com',
  name: 'Current User',
}

function tokenWithClaims(claims: unknown): string {
  const payload = btoa(JSON.stringify(claims)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '')
  return `header.${payload}.signature`
}

afterEach(() => vi.useRealTimers())

describe('isValidTokenExchangeResponse', () => {
  it('accepts a valid response with optional fields omitted', () => {
    expect(isValidTokenExchangeResponse({ access_token: 'access' })).toBe(true)
  })

  it.each([
    null,
    [],
    {},
    { access_token: '' },
    { access_token: 3 },
    { access_token: 'access', refresh_session: 'yes' },
    { access_token: 'access', id_token: 3 },
    { access_token: 'access', expires_in: Number.NaN },
    { access_token: 'access', expires_in: 0 },
    { access_token: 'access', expires_in: '3600' },
  ])('rejects malformed response %s', (value) => {
    expect(isValidTokenExchangeResponse(value)).toBe(false)
  })
})

describe('isValidTokenShape', () => {
  it('accepts a complete token', () => {
    expect(isValidTokenShape(currentToken)).toBe(true)
  })

  it.each([
    null,
    'token',
    { ...currentToken, accessToken: '' },
    { ...currentToken, refreshToken: '' },
    { ...currentToken, idToken: undefined },
    { ...currentToken, expiresAt: Number.POSITIVE_INFINITY },
  ])('rejects an invalid token shape %s', (value) => {
    expect(isValidTokenShape(value)).toBe(false)
  })
})

describe('identityFromTokenExchange', () => {
  it('maps a server-held refresh session without exposing a provider credential', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-09-26T12:00:00Z'))
    const idToken = tokenWithClaims({ sub: 'next-user', email: 'next@example.com', name: 'Next' })
    const result = identityFromTokenExchange(
      {
        access_token: 'new-access',
        id_token: idToken,
        refresh_session: true,
        expires_in: 1800,
      },
      currentToken,
      currentUser,
    )

    expect(result.token).toEqual({
      accessToken: 'new-access',
      idToken,
      refreshToken: REFRESH_SESSION_COORDINATION_ID,
      expiresAt: 1790425800,
    })
    expect(result.user).toEqual({
      sub: 'next-user',
      email: 'next@example.com',
      name: 'Next',
      picture: undefined,
    })
  })

  it('preserves the current coordination id when metadata is omitted', () => {
    const result = identityFromTokenExchange({ access_token: 'not-a-jwt' }, currentToken, currentUser)

    expect(result.token.idToken).toBe(currentToken.idToken)
    expect(result.token.refreshToken).toBe(currentToken.refreshToken)
    expect(result.user).toBe(currentUser)
  })

  it('does not trust non-string claim values as identity fields', () => {
    const result = identityFromTokenExchange(
      { access_token: tokenWithClaims({ sub: 42, email: 7 }) },
      currentToken,
      currentUser,
    )

    expect(result.user).toBe(currentUser)
  })

  it('does not crash on JSON null token payloads', () => {
    expect(() => identityFromTokenExchange(
      { access_token: 'header.bnVsbA.signature' }, currentToken, null,
    )).not.toThrow()
  })
})
