// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { ApiError } from './errors'

/** A leader whose normalised name equals the one being created (no contact data). */
export interface LeaderDuplicateMatch {
  id: string
  name: string
  congregation_id: string | null
  is_active: boolean
}

/** The same-named people of a `LEADER_DUPLICATE` rejection, or `null` for any other error. */
export function parseLeaderDuplicate(error: unknown): LeaderDuplicateMatch[] | null {
  if (!(error instanceof ApiError) || error.status !== 409) return null
  const detail = (error.body as { detail?: { code?: unknown; matches?: unknown } } | undefined)?.detail
  if (detail?.code !== 'LEADER_DUPLICATE' || !Array.isArray(detail.matches)) return null
  return detail.matches as LeaderDuplicateMatch[]
}
