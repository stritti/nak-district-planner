// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, expect, it } from 'vitest'
import { assignmentFor, homeAssignment, leaderCongregationIds } from './leaderAssignments'
import type { LeaderAssignment, LeaderResponse } from './leaders'

const assignment = (id: string, congregation_id: string | null, is_home = false): LeaderAssignment => ({
  id, congregation_id, role: null, is_home, revision: `r-${id}`,
})
const leader = (assignments: LeaderAssignment[]) => ({ assignments }) as LeaderResponse

describe('assignment helpers', () => {
  it('finds the home assignment, falling back to the first one', () => {
    expect(homeAssignment(leader([assignment('a', 'c1'), assignment('b', 'c2', true)]))?.id).toBe('b')
    expect(homeAssignment(leader([assignment('a', 'c1'), assignment('b', 'c2')]))?.id).toBe('a')
    expect(homeAssignment(leader([]))).toBeNull()
  })

  it('finds the assignment of a congregation or of the district level', () => {
    const person = leader([assignment('a', 'c1', true), assignment('b', null)])
    expect(assignmentFor(person, 'c1')?.id).toBe('a')
    expect(assignmentFor(person, null)?.id).toBe('b')
    expect(assignmentFor(person, 'c9')).toBeNull()
  })

  it('lists the assigned congregations without the district level', () => {
    expect(leaderCongregationIds(leader([assignment('a', 'c1', true), assignment('b', null), assignment('c', 'c2')])))
      .toEqual(['c1', 'c2'])
  })
})
