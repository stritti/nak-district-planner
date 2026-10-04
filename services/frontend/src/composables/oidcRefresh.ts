import type { OIDCToken, OIDCUser } from './oidcTypes'
import {
  identityFromTokenExchange,
  isValidTokenExchangeResponse,
  isValidTokenShape,
} from './oidcToken'
import { getCurrentCSRFHeaders } from './useCSRF'

export const REFRESH_TIMEOUT_MS = 35_000
export const CROSS_TAB_WAIT_TIMEOUT_MS = 40_000
export const TRANSIENT_RETRY_DELAY_MS = 30_000
export const ROTATED_TOKEN_TTL_MS = 60_000
export const PERSISTED_RECEIPT_TTL_MS = 24 * 60 * 60 * 1000
export const MAX_PERSISTED_RECEIPTS = 32
export const MAX_RECEIPT_CHAIN_LENGTH = 64

export const RECEIPT_KEY_PREFIX = 'oidc-refresh-result:'

/**
 * Receipt states are kept in sessionStorage, scoped to the current tab.
 * Cross-tab coordination is provided by Web Locks and BroadcastChannel; no
 * provider refresh credential is ever present in JavaScript.
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

/** Decode one tab-local rotation receipt and fail closed for malformed data. */
export function parseStoredReceipt(raw: string | null): StoredReceipt {
  if (raw === null) return { state: 'absent' }
  if (raw === RECEIPT_STATE_PENDING) return { state: 'pending' }
  if (raw === RECEIPT_STATE_CONSUMED) return { state: 'consumed' }
  try {
    const parsed = JSON.parse(raw) as Partial<RotationReceipt>
    if (!parsed || !isValidTokenShape(parsed.token) || !isValidOIDCUser(parsed.user)) return { state: 'invalid' }
    if (typeof parsed.recordedAt !== 'number' || !Number.isFinite(parsed.recordedAt)) return { state: 'invalid' }
    return { state: 'rotation', receipt: parsed as RotationReceipt }
  } catch {
    return { state: 'invalid' }
  }
}

function isValidOIDCUser(value: unknown): value is OIDCUser | null {
  if (value === null) return true
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false
  const user = value as Partial<OIDCUser>
  return typeof user.sub === 'string' && user.sub.length > 0 &&
    (user.email === undefined || typeof user.email === 'string') &&
    (user.name === undefined || typeof user.name === 'string') &&
    (user.picture === undefined || typeof user.picture === 'string')
}

function toBase64Url(bytes: Uint8Array): string {
  const binary = Array.from(bytes, (byte) => String.fromCharCode(byte)).join('')
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '')
}

export async function rotationReceiptKey(refreshToken: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(refreshToken))
  return RECEIPT_KEY_PREFIX + toBase64Url(new Uint8Array(digest))
}

/** Scrub tab-local refresh receipts while retaining replay markers. */
export function clearRotationReceipts(): void {
  try {
    const keys: string[] = []
    for (let i = 0; i < sessionStorage.length; i += 1) {
      const key = sessionStorage.key(i)
      if (!key?.startsWith(RECEIPT_KEY_PREFIX)) continue
      const state = sessionStorage.getItem(key)
      if (state !== RECEIPT_STATE_PENDING && state !== RECEIPT_STATE_CONSUMED) {
        keys.push(key)
      }
    }
    keys.forEach((key) => sessionStorage.setItem(key, RECEIPT_STATE_CONSUMED))
  } catch { /* Storage may be unavailable. */ }
}

export function prunePersistedReceipts(): void {
  const now = Date.now()
  const completed: { key: string; recordedAt: number }[] = []
  for (let i = 0; i < sessionStorage.length; i += 1) {
    const key = sessionStorage.key(i)
    if (!key?.startsWith(RECEIPT_KEY_PREFIX)) continue
    const raw = sessionStorage.getItem(key)
    if (!raw || raw === RECEIPT_STATE_CONSUMED) continue
    try {
      const receipt = JSON.parse(raw) as { recordedAt?: number }
      const recordedAt = receipt.recordedAt
      if (typeof recordedAt !== 'number' || !Number.isFinite(recordedAt) ||
          recordedAt > now || now - recordedAt > PERSISTED_RECEIPT_TTL_MS) {
        sessionStorage.setItem(key, RECEIPT_STATE_CONSUMED)
      } else completed.push({ key, recordedAt })
    } catch {
      // Malformed receipts are handled by fail-closed adoption, not pruning.
    }
  }
  completed.sort((a, b) => b.recordedAt - a.recordedAt)
  for (const entry of completed.slice(MAX_PERSISTED_RECEIPTS)) {
    sessionStorage.setItem(entry.key, RECEIPT_STATE_CONSUMED)
  }
}

type ReceiptClaim = 'proceed' | 'stop' | 'adopt'

export type RefreshChannelMessage =
  | { type: 'refresh-started'; refreshToken: string }
  | { type: 'refresh-complete'; ok: boolean; refreshToken: string; token?: OIDCToken; user?: OIDCUser | null; completedAt?: number }

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

/** Run one refresh attempt under the shared Web Lock. */
export async function runRefreshOperation(options: {
  currentToken: OIDCToken
  refreshTokenUsed: string
  authStoreToken: () => OIDCToken | null
  authStoreUser: () => OIDCUser | null
  fetchUserInfo: (accessToken: string) => Promise<OIDCUser | null>
  isRefreshStillCurrent: () => boolean
  logout: () => Promise<void> | void
  adoptRotatedToken: (token: OIDCToken, user: OIDCUser | null) => void
  onExpiredSuccessor: (token: OIDCToken) => void
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
    onExpiredSuccessor,
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
    pruneRotatedTokens(rotatedTokens)
    const rotated = rotatedTokens.get(refreshTokenUsed)
    if (rotated && isRefreshStillCurrent()) {
      adoptRotatedToken(rotated.token, rotated.user)
      return
    }
    if (isRefreshStillCurrent()) void logout()
  }

  let safeToRetry = false

  const runRefreshBody = async (): Promise<boolean> => {
    let completedOk = false
    let completedToken: OIDCToken | undefined
    let completedUser: OIDCUser | null | undefined
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), REFRESH_TIMEOUT_MS)

    try {
      postRefreshMessage({ type: 'refresh-started', refreshToken: refreshTokenUsed })
      const response = await fetch('/api/v1/auth/oidc/token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getCurrentCSRFHeaders(),
        },
        signal: controller.signal,
        body: JSON.stringify({ grant_type: 'refresh_token' }),
      })

      if (!response.ok) {
        const body = await response.json().catch(() => null)
        const bodyRecord = body && typeof body === 'object' ? (body as Record<string, unknown>) : null
        const detail = bodyRecord?.detail
        const detailRecord = detail && typeof detail === 'object' ? (detail as Record<string, unknown>) : null
        const errorCode = bodyRecord?.error ?? detailRecord?.error
        if (errorCode === 'invalid_grant' || errorCode === 'missing_refresh_cookie') {
          logoutIfRefreshStillCurrent()
          return false
        }
        safeToRetry = response.status === 429
        if (safeToRetry) scheduleTransientRefreshRetry()
        return false
      }

      const data: unknown = await response.json()
      if (!isValidTokenExchangeResponse(data)) return false

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
        const stored = parseStoredReceipt(sessionStorage.getItem(await rotationReceiptKey(next)))
        if (stored.state === 'absent') break
        if (stored.state !== 'rotation') throw new Error(`Unusable refresh receipt state: ${stored.state}`)
        latest = stored.receipt
        if (stored.receipt.token.refreshToken === next) break
        next = stored.receipt.token.refreshToken!
      }
    } catch {
      failClosed()
      return false
    }
    if (!latest || !isRefreshStillCurrent()) return false
    adoptRotatedToken(latest.token, latest.user)
    if (latest.token.expiresAt <= Date.now() / 1000) {
      onExpiredSuccessor(latest.token)
      return false
    }
    return true
  }

  const receiptKey = await rotationReceiptKey(refreshTokenUsed)

  const inspectStoredReceipt = async (): Promise<ReceiptClaim> => {
    try {
      const stored = parseStoredReceipt(sessionStorage.getItem(receiptKey))
      if (stored.state === 'consumed') {
        failClosed()
        return 'stop'
      }
      if (stored.state === 'pending') {
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
          sessionStorage.removeItem(receiptKey)
          sessionStorage.setItem(receiptKey, RECEIPT_STATE_PENDING)
        } else {
          return 'adopt'
        }
      }
      if (sessionStorage.getItem(receiptKey) === null) {
        prunePersistedReceipts()
        sessionStorage.setItem(receiptKey, RECEIPT_STATE_PENDING)
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
          sessionStorage.setItem(receiptKey, JSON.stringify(rotated))
          prunePersistedReceipts()
        } catch {
          const latest = authStoreToken()
          if (latest && latest.refreshToken === rotated.token.refreshToken && latest.accessToken === rotated.token.accessToken) {
            endLocalSession()
          }
          return false
        }
      }
    } else if (safeToRetry) {
      try {
        if (sessionStorage.getItem(receiptKey) === RECEIPT_STATE_PENDING) sessionStorage.removeItem(receiptKey)
      } catch { /* A missing storage facility fails closed on the next attempt. */ }
    } else if (isRefreshStillCurrent()) {
      failClosed()
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
      try {
        if (sessionStorage.getItem(receiptKey) === RECEIPT_STATE_PENDING) sessionStorage.removeItem(receiptKey)
      } catch { /* fail closed */ }
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
