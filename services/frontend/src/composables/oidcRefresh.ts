import type { OIDCToken, OIDCUser } from './useOIDC'
import { identityFromTokenExchange, isValidTokenShape, type TokenExchangeResponse } from './oidcToken'

export const REFRESH_TIMEOUT_MS = 35_000
export const CROSS_TAB_WAIT_TIMEOUT_MS = 40_000
export const TRANSIENT_RETRY_DELAY_MS = 30_000
export const ROTATED_TOKEN_TTL_MS = 60_000
export const PERSISTED_RECEIPT_TTL_MS = 24 * 60 * 60 * 1000
export const MAX_PERSISTED_RECEIPTS = 32
export const MAX_RECEIPT_CHAIN_LENGTH = 64

export const RECEIPT_KEY_PREFIX = 'oidc-refresh-result:'

/**
 * Receipt states persisted in localStorage, keyed by
 * `oidc-refresh-result:<sha256(refreshToken)>` and shared across tabs:
 * - `pending`: another tab may have submitted this refresh token to the
 *   provider; it must never be replayed until the outcome is known.
 * - `consumed`: tombstone; the receipt was completed and compacted. The
 *   refresh token was already used and must not be replayed either.
 * - `rotation`: JSON receipt with the rotated token for the next lock owner.
 */
export const RECEIPT_STATE_PENDING = ''
export const RECEIPT_STATE_CONSUMED = 'consumed'

export interface RotationReceipt {
  token: OIDCToken
  user: OIDCUser | null
  recordedAt: number
}

export type StoredReceipt =
  | { state: 'absent' }
  | { state: 'pending' }
  | { state: 'consumed' }
  | { state: 'rotation'; receipt: RotationReceipt }
  | { state: 'invalid' }

/**
 * Decodes the raw localStorage value of a rotation receipt. Malformed
 * JSON or a receipt that fails token validation yields `invalid`; callers
 * must fail closed for `pending` and `invalid`.
 */
export function parseStoredReceipt(raw: string | null): StoredReceipt {
  if (raw === null) return { state: 'absent' }
  if (raw === RECEIPT_STATE_PENDING) return { state: 'pending' }
  if (raw === RECEIPT_STATE_CONSUMED) return { state: 'consumed' }
  try {
    const parsed = JSON.parse(raw) as Partial<RotationReceipt>
    if (!parsed || !isValidTokenShape(parsed.token)) return { state: 'invalid' }
    if (typeof parsed.recordedAt !== 'number' || !Number.isFinite(parsed.recordedAt)) return { state: 'invalid' }
    return { state: 'rotation', receipt: parsed as RotationReceipt }
  } catch {
    return { state: 'invalid' }
  }
}

function toBase64Url(bytes: Uint8Array): string {
  const binary = Array.from(bytes, (byte) => String.fromCharCode(byte)).join('')
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '')
}

export async function rotationReceiptKey(refreshToken: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(refreshToken))
  return RECEIPT_KEY_PREFIX + toBase64Url(new Uint8Array(digest))
}

/** Removes rotation receipts except pending markers, which protect suspended tabs. */
export function clearRotationReceipts(): void {
  try {
    const keys: string[] = []
    for (let i = 0; i < localStorage.length; i += 1) {
      const key = localStorage.key(i)
      if (key?.startsWith(RECEIPT_KEY_PREFIX) && localStorage.getItem(key) !== RECEIPT_STATE_PENDING) keys.push(key)
    }
    keys.forEach((key) => localStorage.removeItem(key))
  } catch { /* Storage may be unavailable. */ }
}

export function prunePersistedReceipts(): void {
  const now = Date.now()
  const completed: { key: string; recordedAt: number }[] = []
  for (let i = 0; i < localStorage.length; i += 1) {
    const key = localStorage.key(i)
    if (!key?.startsWith(RECEIPT_KEY_PREFIX)) continue
    const raw = localStorage.getItem(key)
    if (!raw || raw === RECEIPT_STATE_CONSUMED) continue // Retain pending markers and replay tombstones.
    try {
      const receipt = JSON.parse(raw) as { recordedAt?: number }
      const recordedAt = receipt.recordedAt
      if (typeof recordedAt !== 'number' || !Number.isFinite(recordedAt) ||
          recordedAt > now || now - recordedAt > PERSISTED_RECEIPT_TTL_MS) {
        localStorage.setItem(key, RECEIPT_STATE_CONSUMED) // Non-secret replay tombstone for suspended tabs.
      } else completed.push({ key, recordedAt })
    } catch {
      // Malformed receipts are handled by fail-closed adoption, not pruning.
    }
  }
  completed.sort((a, b) => b.recordedAt - a.recordedAt)
  for (const entry of completed.slice(MAX_PERSISTED_RECEIPTS)) {
    localStorage.setItem(entry.key, RECEIPT_STATE_CONSUMED)
  }
}

type ReceiptClaim = 'proceed' | 'stop' | 'adopt'

export type RefreshChannelMessage =
  | { type: 'refresh-started'; refreshToken: string }
  | { type: 'refresh-complete'; ok: boolean; refreshToken: string; token?: OIDCToken; user?: OIDCUser | null; completedAt?: number }

/**
 * Shared cross-tab refresh state. Kept at module level so that all
 * composable instances coalesce onto one in-flight refresh.
 */
export interface CrossTabRefreshState {
  inFlight: Promise<boolean> | null
  waiter: { refreshToken: string; resolve: (ok: boolean) => void; timeoutId: ReturnType<typeof setTimeout> } | null
}

export function clearCrossTabWaiter(state: CrossTabRefreshState, resolveWith = false): void {
  if (!state.waiter) return
  clearTimeout(state.waiter.timeoutId)
  const resolve = state.waiter.resolve
  state.waiter = null
  resolve(resolveWith)
}

export function waitForCrossTabRefresh(state: CrossTabRefreshState, refreshToken: string): Promise<boolean> {
  return new Promise<boolean>((resolve) => {
    const timeoutId = setTimeout(() => {
      if (state.waiter?.refreshToken === refreshToken) {
        state.waiter = null
        state.inFlight = null
        resolve(false)
      }
    }, CROSS_TAB_WAIT_TIMEOUT_MS)
    state.waiter = { refreshToken, resolve, timeoutId }
  })
}

/**
 * Runs one refresh attempt under the `oidc-refresh:<token>` Web Lock.
 * The phases — inspectStoredReceipt → adoptLatestReceipt → runRefreshBody
 * → persistRefreshOutcome — previously lived as inline closures inside
 * useOIDC.refreshToken() and were extracted verbatim.
 *
 * Cross-tab coordination (BroadcastChannel + pending receipt markers)
 * guarantees that a rotating refresh token is never replayed after an
 * ambiguous outcome; ambiguous outcomes fail closed.
 */
export async function runRefreshOperation(options: {
  currentToken: OIDCToken
  refreshTokenUsed: string
  authStoreToken: () => OIDCToken | null
  authStoreUser: () => OIDCUser | null
  fetchUserInfo: (accessToken: string) => Promise<OIDCUser | null>
  isRefreshStillCurrent: () => boolean
  logout: () => Promise<void> | void
  adoptRotatedToken: (token: OIDCToken, user: OIDCUser | null) => void
  scheduleTransientRefreshRetry: () => void
  endLocalSession: () => void
  rotatedTokens: Map<string, RotationReceipt>
  crossTabState: CrossTabRefreshState
  postRefreshMessage: (message: RefreshChannelMessage) => void
}): Promise<boolean> {
  const {
    currentToken,
    refreshTokenUsed,
    authStoreToken,
    authStoreUser,
    fetchUserInfo,
    isRefreshStillCurrent,
    logout,
    adoptRotatedToken,
    scheduleTransientRefreshRetry,
    endLocalSession,
    rotatedTokens,
    crossTabState,
    postRefreshMessage,
  } = options

  const failClosed = (): void => {
    if (!isRefreshStillCurrent()) return
    endLocalSession()
  }

  const logoutIfRefreshStillCurrent = (): void => {
    const rotated = rotatedTokens.get(refreshTokenUsed)
    if (rotated && isRefreshStillCurrent()) {
      adoptRotatedToken(rotated.token, rotated.user)
      return
    }
    if (isRefreshStillCurrent()) void logout()
  }

  // Only a definitive pre-provider rejection permits reusing the token.
  // Transport errors, timeouts and malformed responses are ambiguous.
  let safeToRetry = false

  const runRefreshBody = async (): Promise<boolean> => {
    let completedOk = false
    let completedToken: OIDCToken | undefined
    let completedUser: OIDCUser | null | undefined
    const controller = new AbortController()
    // Bound stalled browser-to-backend refresh requests so callers do not share a stuck promise forever.
    const timeoutId = setTimeout(() => controller.abort(), REFRESH_TIMEOUT_MS)

    try {
      postRefreshMessage({ type: 'refresh-started', refreshToken: refreshTokenUsed })
      const response = await fetch('/api/v1/auth/oidc/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          grant_type: 'refresh_token',
          refresh_token: refreshTokenUsed,
        }),
      })

      if (!response.ok) {
        const body = await response.json().catch(() => null)
        const bodyRecord = body && typeof body === 'object' ? (body as Record<string, unknown>) : null
        const detail = bodyRecord?.detail
        const detailRecord = detail && typeof detail === 'object' ? (detail as Record<string, unknown>) : null
        const errorCode = bodyRecord?.error ?? detailRecord?.error
        if (errorCode === 'invalid_grant') {
          logoutIfRefreshStillCurrent()
          return false
        }
        // A rate limit rejects the request before token processing.
        // Other errors (including generic 503) might follow rotation.
        safeToRetry = response.status === 429
        if (safeToRetry) scheduleTransientRefreshRetry()
        return false
      }

      const data = (await response.json()) as TokenExchangeResponse
      if (!data.access_token) {
        return false
      }

      const { token: nextToken, user: derivedUser } = identityFromTokenExchange(data, currentToken, authStoreUser())
      let nextUser: OIDCUser | null = derivedUser
      if (!nextUser?.sub && !authStoreUser()?.sub) {
        nextUser = await fetchUserInfo(data.access_token)
      }

      if (!nextUser?.sub) {
        logoutIfRefreshStillCurrent()
        return false
      }

      if (!isRefreshStillCurrent()) return false

      adoptRotatedToken(nextToken, nextUser)
      rotatedTokens.set(refreshTokenUsed, { token: nextToken, user: nextUser, recordedAt: Date.now() })
      pruneRotatedTokens(rotatedTokens)
      completedOk = true
      completedToken = nextToken
      completedUser = nextUser
      return true
    } catch (err) {
      console.error('OIDC refresh failed', err)
      // The provider might have rotated before the response was lost.
      return false
    } finally {
      clearTimeout(timeoutId)
      postRefreshMessage({
        type: 'refresh-complete',
        ok: completedOk,
        refreshToken: refreshTokenUsed,
        token: completedToken,
        user: completedUser,
        completedAt: Date.now(),
      })
    }
  }

  const adoptLatestReceipt = async (): Promise<boolean> => {
    if (!isRefreshStillCurrent()) return false
    let next = refreshTokenUsed
    const seen = new Set<string>()
    let latest: RotationReceipt | null = null
    try {
      while (!seen.has(next) && seen.size < MAX_RECEIPT_CHAIN_LENGTH) {
        seen.add(next)
        const stored = parseStoredReceipt(localStorage.getItem(await rotationReceiptKey(next)))
        if (stored.state === 'absent') break
        if (stored.state !== 'rotation') throw new Error(`Unusable refresh receipt state: ${stored.state}`)
        latest = stored.receipt
        if (stored.receipt.token.refreshToken === next) break // Non-rotating provider.
        next = stored.receipt.token.refreshToken!
      }
    } catch {
      failClosed()
      return false
    }
    if (!latest || !isRefreshStillCurrent()) return false
    adoptRotatedToken(latest.token, latest.user)
    // Never report success with an expired bearer token.
    if (latest.token.expiresAt <= Date.now() / 1000) {
      scheduleTransientRefreshRetry()
      return false
    }
    return true
  }

  // A lock serializes network requests, but a waiting tab may acquire it
  // before its BroadcastChannel receives the preceding tab's rotation.
  // Persist the rotation receipt while still holding the lock; the next
  // owner must consult it before submitting the captured refresh token.
  const receiptKey = await rotationReceiptKey(refreshTokenUsed)

  const inspectStoredReceipt = async (): Promise<ReceiptClaim> => {
    try {
      const stored = parseStoredReceipt(localStorage.getItem(receiptKey))
      if (stored.state === 'consumed') {
        failClosed() // The token was rotated before this tab was suspended.
        return 'stop'
      }
      if (stored.state === 'pending') {
        // The previous owner may have crashed after submitting a rotating
        // token. Preserve the marker across local logout.
        if (isRefreshStillCurrent()) void logout()
        return 'stop'
      }
      if (stored.state === 'invalid') {
        failClosed()
        return 'stop'
      }
      if (stored.state === 'rotation') {
        const receipt = stored.receipt
        if (receipt.token.refreshToken === refreshTokenUsed &&
            (receipt.token.accessToken === currentToken.accessToken || receipt.token.expiresAt <= Date.now() / 1000)) {
          // A stable refresh token may be reused after the previous
          // completed receipt has been consumed. This check and removal
          // happen exclusively under the Web Lock.
          localStorage.removeItem(receiptKey)
          localStorage.setItem(receiptKey, RECEIPT_STATE_PENDING) // Protect the next request, even if it rotates.
        } else {
          return 'adopt'
        }
      }
      // Shared storage is required to communicate rotation to the next
      // lock owner; without it we cannot safely refresh across tabs.
      if (localStorage.getItem(receiptKey) === null) {
        prunePersistedReceipts()
        localStorage.setItem(receiptKey, RECEIPT_STATE_PENDING)
      }
      return 'proceed'
    } catch {
      failClosed()
      return 'stop'
    }
  }

  const persistRefreshOutcome = (ok: boolean): boolean => {
    if (ok) {
      const rotated = rotatedTokens.get(refreshTokenUsed)
      if (rotated) {
        try {
          localStorage.setItem(receiptKey, JSON.stringify(rotated))
          prunePersistedReceipts()
        } catch {
          // The provider may have rotated: preserve the pending marker,
          // and do not leave an apparently authenticated stale session.
          const latest = authStoreToken()
          if (latest && latest.refreshToken === rotated.token.refreshToken && latest.accessToken === rotated.token.accessToken) {
            endLocalSession()
          }
          return false
        }
      }
    } else if (safeToRetry) {
      // Only definitive pre-provider failures permit reuse.
      // An ambiguous response must retain the pending marker.
      // Never remove a receipt that another operation has replaced.
      try {
        if (localStorage.getItem(receiptKey) === RECEIPT_STATE_PENDING) localStorage.removeItem(receiptKey)
      } catch { /* A missing storage facility fails closed on the next attempt. */ }
    } else {
      // Unknown outcome: the provider may already have rotated. Keep the
      // pending marker so no tab can replay this token, and end this
      // local session without clearing the shared safety marker.
      if (isRefreshStillCurrent()) {
        failClosed()
      }
    }
    return ok
  }

  return navigator.locks.request(`oidc-refresh:${refreshTokenUsed}`, { ifAvailable: true }, async (lock) => {
    if (!lock) {
      const received = await waitForCrossTabRefresh(crossTabState, refreshTokenUsed)
      const latest = authStoreToken()
      if (received && latest && latest.expiresAt > Date.now() / 1000) return true
      return await adoptLatestReceipt()
    }
    const claim = await inspectStoredReceipt()
    if (claim === 'adopt') return await adoptLatestReceipt()
    if (claim === 'stop') return false
    if (!isRefreshStillCurrent()) {
      try { if (localStorage.getItem(receiptKey) === RECEIPT_STATE_PENDING) localStorage.removeItem(receiptKey) } catch { /* fail closed */ }
      return false
    }
    return persistRefreshOutcome(await runRefreshBody())
  })
}

export function pruneRotatedTokens(rotatedTokens: Map<string, RotationReceipt>): void {
  const now = Date.now()
  for (const [refreshToken, entry] of rotatedTokens.entries()) {
    if (now - entry.recordedAt > ROTATED_TOKEN_TTL_MS) rotatedTokens.delete(refreshToken)
  }
}
