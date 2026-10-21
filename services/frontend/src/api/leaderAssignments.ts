// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import type { LeaderAssignment, LeaderResponse } from './leaders'

// Pure helpers over a leader's assignments (no HTTP, unaffected by mocks of `./leaders`).

export function homeAssignment(leader: LeaderResponse): LeaderAssignment | null {
  return leader.assignments.find((a) => a.is_home) ?? leader.assignments[0] ?? null
}

export function assignmentFor(leader: LeaderResponse, congregationId: string | null): LeaderAssignment | null {
  return leader.assignments.find((a) => a.congregation_id === congregationId) ?? null
}

export function leaderCongregationIds(leader: LeaderResponse): string[] {
  return leader.assignments.flatMap((a) => (a.congregation_id ? [a.congregation_id] : []))
}

