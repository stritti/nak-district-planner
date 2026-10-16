// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, expect, it } from 'vitest'
import type { LeaderResponse } from '../../../api/leaders'
import { inlineLeaderPayload, inlineLeaderValue, LIFECYCLE_FIELDS } from '../inlineLeaderFields'

describe('inlineLeaderPayload', () => {
  it.each([
    ['name', 'Anna', { name: 'Anna' }],
    ['email', '', { email: null }],
    ['phone', '123', { phone: '123' }],
    ['rank', 'Pr.', { rank: 'Pr.' }],
    ['special_role', '', { special_role: null }],
    ['special_role', 'Gemeindevorsteher', { special_role: 'Gemeindevorsteher' }],
    ['congregation_id', '', { congregation_id: null }],
    ['congregation_id', 'c1', { congregation_id: 'c1' }],
    ['is_active', 'false', { is_active: false }],
    ['is_active', 'true', { is_active: true }],
  ] as const)('maps %s=%j to exactly one field', (field, value, expected) => {
    expect(inlineLeaderPayload(field, value)).toEqual(expected)
  })
})

describe('inlineLeaderValue', () => {
  const leader = { rank: 'Pr.', special_role: null, is_active: false, email: undefined } as unknown as LeaderResponse

  it('stringifies stored values and maps null/undefined to empty', () => {
    expect(inlineLeaderValue(leader, 'rank')).toBe('Pr.')
    expect(inlineLeaderValue(leader, 'special_role')).toBe('')
    expect(inlineLeaderValue(leader, 'email')).toBe('')
    expect(inlineLeaderValue(leader, 'is_active')).toBe('false')
  })

  it('treats activity as the only lifecycle field', () => {
    expect(LIFECYCLE_FIELDS).toEqual(['is_active'])
  })
})
