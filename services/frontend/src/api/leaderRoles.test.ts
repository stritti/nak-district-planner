// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, expect, it } from 'vitest'
import { roleChoicesFor, roleFitsLevel } from './leaderRoles'

describe('role and level', () => {
  it('lets a congregation leader serve a congregation only', () => {
    expect(roleFitsLevel('Gemeindevorsteher', 'c1')).toBe(true)
    expect(roleFitsLevel('Gemeindevorsteher', null)).toBe(false)
  })

  it('lets a district leader serve the district level only', () => {
    expect(roleFitsLevel('Bezirksvorsteher', null)).toBe(true)
    expect(roleFitsLevel('Bezirksvorsteher', 'c1')).toBe(false)
  })

  it('accepts no role on every level', () => {
    expect(roleFitsLevel(null, 'c1')).toBe(true)
    expect(roleFitsLevel(null, null)).toBe(true)
  })

  it('offers exactly the roles that fit', () => {
    expect(roleChoicesFor('c1').map((r) => r.value)).toEqual(['Gemeindevorsteher'])
    expect(roleChoicesFor(null).map((r) => r.value)).toEqual(['Bezirksvorsteher'])
  })
})
