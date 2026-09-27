import { describe, it, expect } from 'vitest'
import { ConflictError, parseConflictError } from './errors'

describe('parseConflictError', () => {
  const conflictBody = JSON.stringify({
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
  })

  it('parses a structured 409 response from an apiFetch error', () => {
    const apiError = new Error(`409 Conflict: ${conflictBody}`)
    const parsed = parseConflictError(apiError)
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

  it('returns null for non-409 errors', () => {
    expect(parseConflictError(new Error('500 Internal Server Error: oops'))).toBeNull()
    expect(parseConflictError(new Error('irgendwas'))).toBeNull()
    expect(parseConflictError('not an error')).toBeNull()
  })

  it('returns null for 409 responses without a conflict list', () => {
    expect(parseConflictError(new Error('409 Conflict: {"detail": "sonstiges"}'))).toBeNull()
    expect(parseConflictError(new Error('409 Conflict: kein json'))).toBeNull()
    expect(parseConflictError(new Error('409 Conflict: {"detail":{"conflicts":[]}}'))).toBeNull()
  })
})
