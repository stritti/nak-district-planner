// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, it, expect } from 'vitest'
import { isLeaderEligibleOn, type LeaderResponse } from './leaders'

describe('minister service eligibility', () => {
  const leader = { is_active: true, hidden_from_lists: false, service_end_date: '2026-12-31' } as LeaderResponse
  it('includes the last day and excludes the following day', () => {
    expect(isLeaderEligibleOn(leader, '2026-12-31')).toBe(true)
    expect(isLeaderEligibleOn(leader, '2027-01-01')).toBe(false)
  })
  it('excludes hidden and inactive ministers', () => {
    expect(isLeaderEligibleOn({ ...leader, hidden_from_lists: true }, '2026-01-01')).toBe(false)
    expect(isLeaderEligibleOn({ ...leader, is_active: false }, '2026-01-01')).toBe(false)
  })
  it('allows any date without an end date', () => {
    expect(isLeaderEligibleOn({ ...leader, service_end_date: null }, '2030-01-01')).toBe(true)
  })
})
