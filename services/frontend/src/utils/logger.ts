// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

// Central frontend logger (OpenSpec `logging`, docs/operations/logging.md).
// Development writes every level to the console; production builds emit only
// warn/error. Values under sensitive keys are masked, Error objects (including
// Axios errors with their request config) are reduced to name/message/stack,
// and nothing is ever sent to the server.

type Level = 'debug' | 'info' | 'warn' | 'error'
type Sink = Pick<Console, Level>

export type Logger = Record<Level, (...args: unknown[]) => void>

const SENSITIVE_KEY = /token|password|secret|credential|email|name/i
export const REDACTED = '[redacted]'

export function sanitize(value: unknown, seen: WeakSet<object> = new WeakSet()): unknown {
  if (value instanceof Error) {
    return { name: value.name, message: value.message, stack: value.stack }
  }
  if (value === null || typeof value !== 'object') return value
  if (seen.has(value)) return '[circular]'
  seen.add(value)
  if (Array.isArray(value)) return value.map((item) => sanitize(item, seen))
  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [
      key,
      SENSITIVE_KEY.test(key) ? REDACTED : sanitize(item, seen),
    ]),
  )
}

export function createLogger(production: boolean, sink: Sink = console): Logger {
  const emit =
    (level: Level) =>
    (...args: unknown[]) => {
      if (production && (level === 'debug' || level === 'info')) return
      sink[level](...args.map((arg) => sanitize(arg)))
    }
  return { debug: emit('debug'), info: emit('info'), warn: emit('warn'), error: emit('error') }
}

export const logger: Logger = createLogger(import.meta.env.PROD)
