// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, expect, it } from 'vitest'
import { parseJwt } from './jwt'

function tokenWithPayload(payload: unknown): string {
  const json = JSON.stringify(payload)
  const encoded = btoa(new TextEncoder().encode(json).reduce((binary, byte) => binary + String.fromCharCode(byte), ''))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '')
  return `header.${encoded}.signature`
}

describe('parseJwt', () => {
  it('decodes a base64url UTF-8 payload', () => {
    expect(parseJwt(tokenWithPayload({ sub: 'user', name: 'Jörg Müller' }))).toEqual({
      sub: 'user',
      name: 'Jörg Müller',
    })
  })

  it.each([
    '',
    'not-a-jwt',
    'header.!.signature',
    tokenWithPayload(null),
    tokenWithPayload(['not', 'an', 'object']),
  ])('returns an empty claim set for invalid payload %s', (token) => {
    expect(parseJwt(token)).toEqual({})
  })
})
