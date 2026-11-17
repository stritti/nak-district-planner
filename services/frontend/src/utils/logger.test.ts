// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, expect, it, vi } from 'vitest'

import { REDACTED, createLogger, logger, sanitize } from './logger'

function sink() {
  return { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}

describe('logger', () => {
  it('stays silent on debug and info in production builds', () => {
    const out = sink()
    const log = createLogger(true, out)
    log.debug('user', { id: 1, email: 'a@example.org' })
    log.info('hello')
    expect(out.debug).not.toHaveBeenCalled()
    expect(out.info).not.toHaveBeenCalled()
  })

  it('emits warn and error in production', () => {
    const out = sink()
    const log = createLogger(true, out)
    log.warn('careful')
    log.error('broken')
    expect(out.warn).toHaveBeenCalledWith('careful')
    expect(out.error).toHaveBeenCalledWith('broken')
  })

  it('writes every level in development', () => {
    const out = sink()
    const log = createLogger(false, out)
    log.debug('d')
    log.info('i')
    expect(out.debug).toHaveBeenCalledWith('d')
    expect(out.info).toHaveBeenCalledWith('i')
  })

  it('masks sensitive keys, also nested', () => {
    const out = sink()
    createLogger(true, out).error('failed', {
      email: 'a@example.org',
      session: { accessToken: 'abc', displayName: 'Max', role: 'PLANNER' },
      list: [{ password: 'pw' }],
    })
    expect(out.error).toHaveBeenCalledWith('failed', {
      email: REDACTED,
      session: { accessToken: REDACTED, displayName: REDACTED, role: 'PLANNER' },
      list: [{ password: REDACTED }],
    })
  })

  it('reduces errors to name, message and stack and drops request payloads', () => {
    const error = Object.assign(new Error('Request failed'), {
      config: { data: '{"password":"pw"}' },
    })
    const result = sanitize(error) as Record<string, unknown>
    expect(Object.keys(result).sort()).toEqual(['message', 'name', 'stack'])
    expect(result.message).toBe('Request failed')
  })

  it('keeps primitives and handles circular objects', () => {
    const circular: Record<string, unknown> = { id: 1 }
    circular.self = circular
    expect(sanitize(null)).toBeNull()
    expect(sanitize(3)).toBe(3)
    expect(sanitize(circular)).toEqual({ id: 1, self: '[circular]' })
  })

  it('exposes a default logger that writes to the console', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    logger.error('x')
    expect(spy).toHaveBeenCalledWith('x')
    spy.mockRestore()
  })
})
