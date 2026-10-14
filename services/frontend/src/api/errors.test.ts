// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, it, expect } from 'vitest'
import { ApiError, ConflictError, parseConflictError } from './errors'

describe('parseConflictError', () => {
  const conflictBody = {
    detail: {
      conflicts: [
        {
          rule_id: 'no_double_booking',
          severity: 'BLOCK',
          message: 'Amtsträger ist bereits zugewiesen',
          details: {},
        },
        {
          rule_id: 'travel_time_check',
          severity: 'WARN',
          message: 'Wechselzeit unterschritten',
          details: {},
        },
      ],
    },
  }

  it('parses a structured 409 response from an apiFetch error', () => {
    const parsed = parseConflictError(new ApiError(409, 'Conflict', conflictBody))
    expect(parsed).toBeInstanceOf(ConflictError)
    expect(parsed?.conflicts).toHaveLength(2)
    expect(parsed?.blocking).toHaveLength(1)
    expect(parsed?.warnings).toHaveLength(1)
    expect(parsed?.blocking[0].rule_id).toBe('no_double_booking')
  })

  it('returns the same instance for ConflictError input', () => {
    const err = new ConflictError([])
    expect(parseConflictError(err)).toBe(err)
  })

  it('treats unknown severities as blocking (fail safe)', () => {
    const parsed = parseConflictError(
      new ApiError(409, 'Conflict', {
        detail: { conflicts: [{ rule_id: 'future_rule', severity: 'ERROR', message: 'Neu', details: {} }] },
      }),
    )
    expect(parsed?.blocking).toHaveLength(1)
    expect(parsed?.warnings).toHaveLength(0)
  })

  it('returns null for non-409 errors and non-ApiError inputs', () => {
    expect(parseConflictError(new ApiError(500, 'Internal Server Error', { detail: 'oops' }))).toBeNull()
    expect(parseConflictError(new Error('irgendwas'))).toBeNull()
    expect(parseConflictError('not an error')).toBeNull()
  })

  it('returns null for 409 responses without a conflict list', () => {
    expect(parseConflictError(new ApiError(409, 'Conflict', { detail: 'sonstiges' }))).toBeNull()
    expect(parseConflictError(new ApiError(409, 'Conflict', 'kein json'))).toBeNull()
    expect(parseConflictError(new ApiError(409, 'Conflict', { detail: { conflicts: [] } }))).toBeNull()
  })
})
