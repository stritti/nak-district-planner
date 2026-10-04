import type { OIDCToken, OIDCUser } from './oidcTypes'
import { identityFromTokenExchange, isValidTokenExchangeResponse } from './oidcToken'
import { getCurrentCSRFHeaders } from './useCSRF'

export const REFRESH_TIMEOUT_MS = 35_000
export const CROSS_TAB_WAIT_TIMEOUT_MS = 40_000
export const TRANSIENT_RETRY_DELAY_MS = 30_000

export type RefreshChannelMessage =
  | { type: 'refresh-started'; sessionId: string }
  | {
      type: 'refresh-complete'
      ok: boolean
      sessionId: string
      token?: OIDCToken
      user?: OIDCUser | null
      completedAt?: number
    }

export interface CrossTabRefreshState {
  inFlight: Promise<boolean> | null
  waiter: {
    sessionId: string
    resolve: (ok: boolean) => void
    timeoutId: ReturnType<typeof setTimeout>
  } | null
}

export function clearCrossTabWaiter(state: CrossTabRefreshState, resolveWith = false): void {
  if (!state.waiter) return
  clearTimeout(state.waiter.timeoutId)
  const resolve = state.waiter.resolve
  state.waiter = null
  resolve(resolveWith)
}

export function waitForCrossTabRefresh(
  state: CrossTabRefreshState,
  sessionId: string,
): Promise<boolean> {
  return new Promise<boolean>((resolve) => {
    const timeoutId = setTimeout(() => {
      if (state.waiter?.sessionId === sessionId) {
        state.waiter = null
        state.inFlight = null
        resolve(false)
      }
    }, CROSS_TAB_WAIT_TIMEOUT_MS)
    state.waiter = { sessionId, resolve, timeoutId }
  })
}

/**
 * Refresh a server-held OIDC session under a cross-tab Web Lock.
 *
 * The browser never owns the provider refresh credential. Web Locks only
 * serialize cookie-backed refresh calls so providers with refresh-token
 * rotation cannot receive two concurrent requests with the same cookie.
 */
export async function runRefreshOperation(options: {
  currentToken: OIDCToken
  sessionId: string
  authStoreUser: () => OIDCUser | null
  fetchUserInfo: (accessToken: string) => Promise<OIDCUser | null>
  isRefreshStillCurrent: () => boolean
  logout: () => Promise<void> | void
  adoptRefreshedToken: (token: OIDCToken, user: OIDCUser | null) => void
  scheduleTransientRefreshRetry: () => void
  endLocalSession: () => void
  crossTabState: CrossTabRefreshState
  postRefreshMessage: (message: RefreshChannelMessage) => void
}): Promise<boolean> {
  const {
    currentToken,
    sessionId,
    authStoreUser,
    fetchUserInfo,
    isRefreshStillCurrent,
    logout,
    adoptRefreshedToken,
    scheduleTransientRefreshRetry,
    endLocalSession,
    crossTabState,
    postRefreshMessage,
  } = options

  const failClosed = (): void => {
    if (isRefreshStillCurrent()) endLocalSession()
  }

  const logoutIfCurrent = (): void => {
    if (isRefreshStillCurrent()) void logout()
  }

  const runRefreshBody = async (): Promise<boolean> => {
    let completedOk = false
    let completedToken: OIDCToken | undefined
    let completedUser: OIDCUser | null | undefined
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), REFRESH_TIMEOUT_MS)

    try {
      postRefreshMessage({ type: 'refresh-started', sessionId })
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
        const bodyRecord = body && typeof body === 'object'
          ? (body as Record<string, unknown>)
          : null
        const detail = bodyRecord?.detail
        const detailRecord = detail && typeof detail === 'object'
          ? (detail as Record<string, unknown>)
          : null
        const errorCode = bodyRecord?.error ?? detailRecord?.error

        if (errorCode === 'invalid_grant' || errorCode === 'missing_refresh_cookie') {
          logoutIfCurrent()
          return false
        }
        if (response.status === 429) {
          scheduleTransientRefreshRetry()
          return false
        }

        // A non-rate-limit failure can be ambiguous with respect to provider
        // token rotation. Do not issue another automatic refresh from this
        // session; clear local auth and require a clean login/restore.
        failClosed()
        return false
      }

      const data: unknown = await response.json()
      if (!isValidTokenExchangeResponse(data) || data.refresh_session !== true) {
        failClosed()
        return false
      }

      const { token: nextToken, user: derivedUser } = identityFromTokenExchange(
        data,
        currentToken,
        authStoreUser(),
      )
      let nextUser: OIDCUser | null = derivedUser
      if (!nextUser?.sub && !authStoreUser()?.sub) {
        nextUser = await fetchUserInfo(data.access_token)
      }

      if (!nextUser?.sub) {
        logoutIfCurrent()
        return false
      }
      if (!isRefreshStillCurrent()) return false

      adoptRefreshedToken(nextToken, nextUser)
      completedOk = true
      completedToken = nextToken
      completedUser = nextUser
      return true
    } catch (error) {
      console.error('OIDC refresh failed', error)
      failClosed()
      return false
    } finally {
      clearTimeout(timeoutId)
      postRefreshMessage({
        type: 'refresh-complete',
        ok: completedOk,
        sessionId,
        token: completedToken,
        user: completedUser,
        completedAt: Date.now(),
      })
    }
  }

  return navigator.locks.request(
    `oidc-refresh:${sessionId}`,
    { ifAvailable: true },
    async (lock) => {
      if (!lock) {
        return waitForCrossTabRefresh(crossTabState, sessionId)
      }
      if (!isRefreshStillCurrent()) return false
      return runRefreshBody()
    },
  )
}
