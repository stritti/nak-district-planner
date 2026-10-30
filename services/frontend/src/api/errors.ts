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

const STATUS_MESSAGES: Record<number, string> = {
  400: 'Die Anfrage ist ungültig. Bitte die Eingaben prüfen.',
  401: 'Die Anmeldung ist abgelaufen. Bitte erneut anmelden.',
  403: 'Für diese Aktion fehlt die Berechtigung.',
  404: 'Der Eintrag wurde nicht gefunden. Vielleicht wurde er inzwischen gelöscht.',
  409: 'Die Änderung steht im Konflikt mit dem aktuellen Stand. Bitte neu laden.',
  412: 'Der Eintrag wurde inzwischen geändert. Bitte neu laden und erneut versuchen.',
  422: 'Die Eingaben sind unvollständig oder ungültig.',
  428: 'Die Versionsinformation fehlt. Bitte neu laden und erneut versuchen.',
  429: 'Zu viele Anfragen. Bitte einen Moment warten und erneut versuchen.',
}

const SERVER_ERROR_MESSAGE =
  'Der Server konnte die Anfrage gerade nicht verarbeiten. Bitte später erneut versuchen.'
const NETWORK_ERROR_MESSAGE = 'Keine Verbindung zum Server. Bitte die Verbindung prüfen.'

/** Plain-text `detail`, or the `message` of a structured `{code, message}` detail. */
function serverDetail(body: unknown): string | null {
  const detail = (body as { detail?: unknown } | undefined)?.detail
  if (typeof detail === 'string') return detail || null
  const message = (detail as { message?: unknown } | null | undefined)?.message
  return typeof message === 'string' && message ? message : null
}

/** fetch() rejects with a TypeError when the network or the server is unreachable. */
function isNetworkError(error: unknown): boolean {
  return error instanceof TypeError && /fetch|network|load failed/i.test(error.message)
}

/**
 * User-facing text of a failed request, the same for every view.
 *
 * The server's text (plain `detail` or `detail.message`) is shown for 400, 404, 409 and
 * 422, for example a taken name. Other statuses get a fixed German text: a 403 detail can be a technical
 * reason (CSRF, token), and 5xx details are never shown. Network failures and an
 * expired session have their own text; other errors keep their message, and
 * non-errors get the fallback.
 */
export function userMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    const detail = serverDetail(error.body)
    if ([400, 404, 409, 422].includes(error.status) && detail) return detail
    if (error.status >= 500) return SERVER_ERROR_MESSAGE
    return STATUS_MESSAGES[error.status] ?? fallback
  }
  if (error instanceof UnauthorizedError) return STATUS_MESSAGES[401]
  if (isNetworkError(error)) return NETWORK_ERROR_MESSAGE
  return error instanceof Error && error.message ? error.message : fallback
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
