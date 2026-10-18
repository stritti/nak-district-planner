// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, expect, it } from 'vitest'
import { ApiError } from './errors'
import { parseLeaderDuplicate } from './leaderDuplicate'

const match = { id: 'l1', name: 'Hans Müller', congregation_id: null, is_active: true }

describe('parseLeaderDuplicate', () => {
  it('returns the matches of a LEADER_DUPLICATE rejection', () => {
    const error = new ApiError(409, 'Conflict', { detail: { code: 'LEADER_DUPLICATE', matches: [match] } })
    expect(parseLeaderDuplicate(error)).toEqual([match])
  })

  it.each([
    ['another 409', new ApiError(409, 'Conflict', { detail: 'Eine Gemeinde existiert bereits' })],
    ['another code', new ApiError(409, 'Conflict', { detail: { code: 'OTHER', matches: [] } })],
    ['missing matches', new ApiError(409, 'Conflict', { detail: { code: 'LEADER_DUPLICATE' } })],
    ['another status', new ApiError(422, 'Unprocessable', { detail: { code: 'LEADER_DUPLICATE', matches: [match] } })],
    ['no body', new ApiError(409, 'Conflict', undefined)],
    ['a plain error', new Error('x')],
  ])('ignores %s', (_label, error) => {
    expect(parseLeaderDuplicate(error)).toBeNull()
  })
})
