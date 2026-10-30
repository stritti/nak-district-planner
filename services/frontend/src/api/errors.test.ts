// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, it, expect } from 'vitest'
import { ApiError, ConflictError, UnauthorizedError, parseConflictError, userMessage } from './errors'

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

describe('userMessage', () => {
  it('shows the plain server detail for 400, 404, 409 and 422', () => {
    expect(userMessage(new ApiError(409, 'Conflict', { detail: 'Eine Gemeinde mit diesem Namen existiert bereits' }), 'x'))
      .toBe('Eine Gemeinde mit diesem Namen existiert bereits')
    expect(userMessage(new ApiError(422, 'Unprocessable', { detail: 'Ungültig' }), 'x')).toBe('Ungültig')
    expect(userMessage(new ApiError(400, 'Bad Request', { detail: 'Ende vor Beginn' }), 'x')).toBe('Ende vor Beginn')
    expect(userMessage(new ApiError(404, 'Not Found', { detail: 'Bezirk nicht gefunden' }), 'x'))
      .toBe('Bezirk nicht gefunden')
    const coded = { detail: { code: 'home_required', message: 'Die Heimat-Zuordnung kann nicht entfernt werden.' } }
    expect(userMessage(new ApiError(409, 'Conflict', coded), 'x')).toBe('Die Heimat-Zuordnung kann nicht entfernt werden.')
  })

  it('uses a fixed text per status for structured, empty or missing details', () => {
    const structured = new ApiError(409, 'Conflict', { detail: { conflicts: [] } }, '{"detail":{}}')
    expect(userMessage(structured, 'x')).toBe(
      'Die Änderung steht im Konflikt mit dem aktuellen Stand. Bitte neu laden.',
    )
    expect(userMessage(new ApiError(409, 'Conflict', { detail: '' }, ''), 'x')).toContain('Konflikt')
    expect(userMessage(new ApiError(409, 'Conflict', undefined), 'x')).toContain('Konflikt')
    expect(userMessage(new ApiError(422, 'Unprocessable', { detail: [{ loc: ['body'] }] }), 'x'))
      .toBe('Die Eingaben sind unvollständig oder ungültig.')
    expect(userMessage(new ApiError(400, 'Bad Request', undefined), 'x')).toContain('ungültig')
    expect(userMessage(new ApiError(404, 'Not Found', undefined), 'x')).toContain('nicht gefunden')
    expect(userMessage(new ApiError(412, 'Precondition Failed', {}), 'x')).toContain('inzwischen geändert')
    expect(userMessage(new ApiError(428, 'Precondition Required', {}), 'x')).toContain('Versionsinformation')
    expect(userMessage(new ApiError(429, 'Too Many Requests', {}), 'x')).toContain('Zu viele Anfragen')
  })

  it('never shows the detail of 403 and server errors', () => {
    expect(userMessage(new ApiError(403, 'Forbidden', { detail: 'CSRF token missing' }), 'x'))
      .toBe('Für diese Aktion fehlt die Berechtigung.')
    const server = new ApiError(500, 'Server Error', { detail: 'intern' }, 'intern')
    expect(userMessage(server, 'x')).toBe(
      'Der Server konnte die Anfrage gerade nicht verarbeiten. Bitte später erneut versuchen.',
    )
    expect(userMessage(new ApiError(503, 'Unavailable', 'down', 'down'), 'x')).toContain('später erneut')
  })

  it('names an expired session and a lost connection', () => {
    expect(userMessage(new UnauthorizedError(), 'x')).toBe('Die Anmeldung ist abgelaufen. Bitte erneut anmelden.')
    expect(userMessage(new TypeError('Failed to fetch'), 'x')).toBe(
      'Keine Verbindung zum Server. Bitte die Verbindung prüfen.',
    )
    expect(userMessage(new TypeError('NetworkError when attempting to fetch resource.'), 'x'))
      .toContain('Keine Verbindung')
  })

  it('keeps other error messages and falls back for non-errors', () => {
    expect(userMessage(new Error('Netz weg'), 'x')).toBe('Netz weg')
    expect(userMessage(new TypeError('x is undefined'), 'Fehler')).toBe('x is undefined')
    expect(userMessage(new Error(''), 'Fehler')).toBe('Fehler')
    expect(userMessage(new ApiError(418, 'Teapot', {}), 'Fehler')).toBe('Fehler')
    expect(userMessage('kaputt', 'Fehler')).toBe('Fehler')
  })
})
