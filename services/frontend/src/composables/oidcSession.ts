import type { OIDCToken, OIDCUser } from './oidcTypes'
import { clearRotationReceipts } from './oidcRefresh'

export const SESSION_CODE_VERIFIER_KEY = 'oidc_code_verifier'
export const SESSION_STATE_KEY = 'oidc_state'

/**
 * Module-level session identity. Advancing the generation invalidates all
 * in-flight refresh operations of the previous session, so stale results
 * can no longer adopt a newer session's state.
 */
let sessionGeneration = 0
let refreshInFlightId = 0

interface SessionLifecycleHost {
  invalidateCrossTabState(): void
  clearTimers(): void
  scheduleRefresh(token: OIDCToken | null): void
}

let host: SessionLifecycleHost | null = null

export function bindSessionLifecycle(bindings: SessionLifecycleHost): void {
  host = bindings
}

export function getSessionGeneration(): number {
  return sessionGeneration
}

export function advanceSessionGeneration(): void {
  sessionGeneration += 1
  refreshInFlightId += 1
  if (host) {
    host.invalidateCrossTabState()
    host.clearTimers()
  }
}

export function nextRefreshOperationId(): number {
  refreshInFlightId += 1
  return refreshInFlightId
}

export function isLatestRefreshOperation(operationId: number): boolean {
  return refreshInFlightId === operationId
}

export function clearLocalArtifacts(): void {
  sessionStorage.removeItem(SESSION_CODE_VERIFIER_KEY)
  sessionStorage.removeItem(SESSION_STATE_KEY)
}

/**
 * Ends the local session while preserving the non-secret replay markers that
 * suspended tabs rely on for token-replay protection.
 */
export function endLocalSession(clearAuth: () => void, navigateToLogin: () => void): void {
  advanceSessionGeneration()
  clearRotationReceipts()
  clearAuth()
  navigateToLogin()
}

export function installSessionToken(
  setAuth: (token: OIDCToken | null, user: OIDCUser | null) => void,
  token: OIDCToken | null,
  user: OIDCUser | null,
): void {
  // advanceSessionGeneration() already ran during invalidation; installing
  // the new token must not advance it again — the refresh pipeline treats
  // the post-invalidation generation as the new session's identity.
  clearRotationReceipts()
  setAuth(token, user)
  host?.scheduleRefresh(token)
}
