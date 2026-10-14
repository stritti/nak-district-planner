// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

export class UnauthorizedError extends Error {
  constructor(cause?: unknown) {
    super('Unauthorized')
    this.name = 'UnauthorizedError'
    if (cause !== undefined) this.cause = cause
  }
}

/**
 * Thrown by apiFetch for non-OK responses.
 * Carries the HTTP status and the parsed body so callers can
 * react to structured error payloads without string matching.
 */
export class ApiError extends Error {
  readonly status: number
  readonly body: unknown

  constructor(status: number, statusText: string, body: unknown, rawText?: string) {
    const text = rawText ?? (body === undefined || body === null ? '' : String(body))
    super(`${status} ${statusText}${text ? `: ${text}` : ''}`)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

export type ConflictSeverity = 'PASS' | 'WARN' | 'BLOCK'

export interface ConflictItem {
  rule_id: string
  severity: ConflictSeverity
  message: string
  details: Record<string, unknown>
}

/**
 * Thrown when the backend rejects an assignment with 409.
 * Carries the structured conflict list from the API response.
 */
export class ConflictError extends Error {
  readonly conflicts: ConflictItem[]

  constructor(conflicts: ConflictItem[]) {
    super('Zuweisung wurde aufgrund von Konflikten abgelehnt')
    this.name = 'ConflictError'
    this.conflicts = conflicts
  }

  /**
   * Everything that is not explicitly overridable or passing blocks the
   * assignment. Unknown severities from newer backend versions fail safe.
   */
  get blocking(): ConflictItem[] {
    return this.conflicts.filter((c) => c.severity !== 'WARN' && c.severity !== 'PASS')
  }

  get warnings(): ConflictItem[] {
    return this.conflicts.filter((c) => c.severity === 'WARN')
  }
}

/**
 * Extracts a structured ConflictError from an apiFetch failure.
 */
export function parseConflictError(error: unknown): ConflictError | null {
  if (error instanceof ConflictError) return error
  if (!(error instanceof ApiError) || error.status !== 409) return null
  const detail = (error.body as { detail?: { conflicts?: unknown } } | null)?.detail
  const conflicts = detail?.conflicts
  if (Array.isArray(conflicts) && conflicts.length > 0) {
    return new ConflictError(conflicts as ConflictItem[])
  }
  return null
}
