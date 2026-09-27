export class UnauthorizedError extends Error {
  constructor(cause?: unknown) {
    super('Unauthorized - please log in again', { cause })
    this.name = 'UnauthorizedError'
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

  get blocking(): ConflictItem[] {
    return this.conflicts.filter((c) => c.severity === 'BLOCK')
  }

  get warnings(): ConflictItem[] {
    return this.conflicts.filter((c) => c.severity === 'WARN')
  }
}

/**
 * Extracts a structured ConflictError from an apiFetch error message.
 * apiFetch throws Error("409 Conflict: {json}") for non-OK responses.
 */
export function parseConflictError(error: unknown): ConflictError | null {
  if (error instanceof ConflictError) return error
  if (!(error instanceof Error)) return null
  const match = error.message.match(/^409[^:]*: (.*)$/s)
  if (!match) return null
  try {
    const parsed = JSON.parse(match[1]) as { detail?: { conflicts?: ConflictItem[] } }
    const conflicts = parsed?.detail?.conflicts
    if (Array.isArray(conflicts) && conflicts.length > 0) {
      return new ConflictError(conflicts)
    }
  } catch {
    // Not a JSON body — not a structured conflict response
  }
  return null
}
