import { computed } from 'vue'
import { useRouter, type Router } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import type { OIDCConfig, OIDCToken, OIDCUser } from './oidcTypes'
import { isValidTokenShape } from './oidcToken'
import {
  clearCrossTabWaiter as clearWaiter,
  clearRotationReceipts,
  type CrossTabRefreshState,
  type RefreshChannelMessage,
  type RotationReceipt,
  pruneRotatedTokens,
  runRefreshOperation,
  TRANSIENT_RETRY_DELAY_MS,
  waitForCrossTabRefresh,
} from './oidcRefresh'
import {
  ACTIVITY_REFRESH_LEAD_SECONDS,
  bindRefreshScheduler,
  clearRefreshTimer,
  clearTransientRetryTimer,
  getRefreshChannel,
  isRefreshChannelListenerAttached,
  markRefreshChannelListenerAttached,
  postRefreshMessage,
  scheduleRefreshTimer,
  scheduleTransientRetry,
  setupActivityRefresh,
  __resetSchedulerState,
} from './refreshScheduler'
import {
  __resetSessionLifecycle,
  advanceSessionGeneration,
  bindSessionLifecycle,
  clearLocalArtifacts,
  endLocalSession,
  getSessionGeneration,
  installSessionToken,
  isLatestRefreshOperation,
  nextRefreshOperationId,
} from './oidcSession'
import { __resetDiscoveryState, loadDiscovery, useDiscoveryState } from './oidcDiscovery'
import {
  exchangeCodeForToken as runCodeExchange,
  getAuthorizationUrl as buildAuthorizationUrl,
} from './oidcAuthorization'
import { restoreRefreshSession } from './oidcSessionRestore'

export type { OIDCConfig, OIDCDiscovery, OIDCToken, OIDCUser } from './oidcTypes'

const envConfig: OIDCConfig = {
  redirectUri: `${window.location.origin}/auth/callback`,
  scope: import.meta.env.VITE_OIDC_SCOPE || 'openid profile email',
}

// Module-level guards: the cross-tab protocol and the rotated-token memory
// are shared by all composable instances by design — one browser profile
// performs exactly one refresh per server-held refresh session.
let lastAdoptedBroadcastAt = 0
const rotatedTokens = new Map<string, RotationReceipt>()
const crossTabState: CrossTabRefreshState = { inFlight: null, waiter: null }
let restoreInFlight: Promise<boolean> | null = null

/** @internal — resets module-level state; used by tests */
export function __resetOIDCModuleState(): void {
  crossTabState.inFlight = null
  if (crossTabState.waiter) clearTimeout(crossTabState.waiter.timeoutId)
  crossTabState.waiter = null
  restoreInFlight = null
  rotatedTokens.clear()
  lastAdoptedBroadcastAt = 0
  __resetSchedulerState()
  __resetDiscoveryState()
  __resetSessionLifecycle()
}

export function useOIDC(router?: Router, config?: Partial<OIDCConfig>) {
  let injectedRouter: Router | null = router || null
  const authStore = useAuthStore()
  const oidcConfig: OIDCConfig = { ...envConfig, ...(config || {}) }
  const { discovery, clientId, isLoading, error } = useDiscoveryState()

  const token = computed(() => authStore.token)
  const user = computed(() => authStore.user)
  const isAuthenticated = computed(() => authStore.isAuthenticated)
  const isTokenExpired = computed(() => {
    if (!authStore.token) return true
    return Date.now() / 1000 >= authStore.token.expiresAt
  })

  function getRouter(): Router {
    if (!injectedRouter) injectedRouter = useRouter()
    return injectedRouter
  }

  function scheduleRefreshFor(token: OIDCToken | null): void {
    if (token) scheduleRefreshTimer(token.expiresAt)
  }

  bindSessionLifecycle({
    invalidateCrossTabState: () => {
      crossTabState.inFlight = null
      clearWaiter(crossTabState, false)
    },
    clearTimers: () => {
      clearRefreshTimer()
      clearTransientRetryTimer()
    },
    scheduleRefresh: scheduleRefreshFor,
  })

  bindRefreshScheduler({
    onScheduledRefresh: () => { void refreshToken() },
    onActivityRefresh: () => {
      const current = authStore.token
      if (!current || crossTabState.inFlight) return
      const secondsUntilExpiry = current.expiresAt - Date.now() / 1000
      if (secondsUntilExpiry < ACTIVITY_REFRESH_LEAD_SECONDS) void refreshToken()
    },
  })

  async function fetchUserInfo(accessToken: string): Promise<OIDCUser | null> {
    const endpoint = discovery.value?.userinfo_endpoint
    if (!endpoint) return null

    const response = await fetch(endpoint, {
      headers: { Authorization: `Bearer ${accessToken}` },
    })

    if (!response.ok) return null

    const data: unknown = await response.json()
    if (!data || typeof data !== 'object' || Array.isArray(data)) return null
    const record = data as Partial<OIDCUser>
    if (typeof record.sub !== 'string' || record.sub.length === 0) return null

    return {
      sub: record.sub,
      email: typeof record.email === 'string' ? record.email : undefined,
      name: typeof record.name === 'string' ? record.name : undefined,
      picture: typeof record.picture === 'string' ? record.picture : undefined,
    }
  }

  function adoptRotatedToken(token: OIDCToken, nextUser: OIDCUser | null): void {
    clearTransientRetryTimer()
    authStore.setToken(token, nextUser ?? authStore.user)
    scheduleRefreshTimer(token.expiresAt)
  }

  function navigateToLogin(): void {
    try { void getRouter().push('/login').catch(() => {}) } catch { /* Router unavailable during startup. */ }
  }

  function setToken(nextToken: OIDCToken | null, nextUser: OIDCUser | null = null): void {
    advanceSessionGeneration()
    installSessionToken((t, u) => authStore.setToken(t, u), nextToken, nextUser)
  }

  async function logout(): Promise<void> {
    advanceSessionGeneration()
    clearRotationReceipts()
    clearLocalArtifacts()
    authStore.clearAuth()

    // Local logout is immediate. The backend owns the provider refresh token,
    // so revocation is a cookie-based best-effort call without a browser token.
    try {
      await fetch('/api/v1/auth/oidc/revoke', {
        method: 'POST',
        signal: AbortSignal.timeout(2_000),
      }).catch(() => {
        // ignore remote logout errors
      })
    } finally {
      try {
        await getRouter().push('/login')
      } catch {
        // router can be unavailable during startup/tests
      }
    }
  }

  function setupRefreshChannelListener(): void {
    if (isRefreshChannelListenerAttached()) return
    const channel = getRefreshChannel()
    if (!channel) return
    markRefreshChannelListenerAttached()

    channel.onmessage = (event: MessageEvent<RefreshChannelMessage>) => {
      const message = event.data
      const currentRefreshToken = authStore.token?.refreshToken
      if (!currentRefreshToken || message.refreshToken !== currentRefreshToken) return

      if (message.type === 'refresh-started') {
        if (crossTabState.inFlight) return
        crossTabState.inFlight = waitForCrossTabRefresh(crossTabState, message.refreshToken)
        return
      }

      if (message.ok && message.token) {
        if (!isValidTokenShape(message.token)) {
          clearWaiter(crossTabState, false)
          crossTabState.inFlight = null
          return
        }
        const completedAt = typeof message.completedAt === 'number' ? message.completedAt : Date.now()
        if (completedAt < lastAdoptedBroadcastAt) return
        lastAdoptedBroadcastAt = completedAt
        rotatedTokens.set(message.refreshToken, {
          token: message.token,
          user: message.user ?? authStore.user,
          recordedAt: completedAt,
        })
        pruneRotatedTokens(rotatedTokens)
        adoptRotatedToken(message.token, message.user ?? authStore.user)
        clearWaiter(crossTabState, true)
      } else {
        clearWaiter(crossTabState, false)
      }
      crossTabState.inFlight = null
    }
  }

  const authorizationDeps = {
    config: oidcConfig,
    getClientId: () => clientId.value,
    getDiscovery: () => discovery.value,
    loadDiscovery,
    fetchUserInfo,
    onSessionInstalled: (nextToken: unknown, nextUser: OIDCUser | null) => {
      setToken(nextToken as OIDCToken, nextUser)
    },
  }

  async function refreshToken(): Promise<boolean> {
    if (crossTabState.inFlight) return crossTabState.inFlight

    const followUp: { expiredSuccessor?: { token: OIDCToken; generation: number } } = {}
    const operation: Promise<boolean> = (async () => {
      const current = authStore.token
      if (!current?.refreshToken) {
        await logout()
        return false
      }
      const refreshGeneration = getSessionGeneration()
      const refreshTokenUsed = current.refreshToken
      const isRefreshStillCurrent = (): boolean => {
        const latest = authStore.token
        return (
          refreshGeneration === getSessionGeneration() &&
          Boolean(latest) &&
          latest?.refreshToken === refreshTokenUsed
        )
      }

      if (typeof navigator === 'undefined' || !navigator.locks) {
        if (current.expiresAt <= Date.now() / 1000 && isRefreshStillCurrent()) {
          void logout()
        } else if (isRefreshStillCurrent()) {
          setTimeout(() => {
            if (isRefreshStillCurrent() && current.expiresAt <= Date.now() / 1000) void logout()
          }, Math.max(0, current.expiresAt * 1000 - Date.now()))
        }
        return false
      }

      return runRefreshOperation({
        currentToken: current,
        refreshTokenUsed,
        authStoreToken: () => authStore.token,
        authStoreUser: () => authStore.user,
        fetchUserInfo,
        isRefreshStillCurrent,
        logout,
        adoptRotatedToken: (token, nextUser) => {
          authStore.setToken(token, nextUser ?? authStore.user)
          clearTransientRetryTimer()
          scheduleRefreshTimer(token.expiresAt)
        },
        onExpiredSuccessor: (token) => {
          followUp.expiredSuccessor = { token, generation: getSessionGeneration() }
        },
        scheduleTransientRefreshRetry: () => {
          const currentToken = authStore.token
          if (!currentToken) return
          if (Date.now() / 1000 < currentToken.expiresAt) {
            scheduleRefreshTimer(currentToken.expiresAt)
            return
          }
          scheduleTransientRetry(TRANSIENT_RETRY_DELAY_MS)
        },
        endLocalSession: () => {
          endLocalSession(() => authStore.clearAuth(), navigateToLogin)
        },
        rotatedTokens,
        crossTabState,
        postRefreshMessage,
      })
    })()

    const operationId = nextRefreshOperationId()
    crossTabState.inFlight = operation
    let result: boolean
    try {
      result = await operation
    } finally {
      if (isLatestRefreshOperation(operationId)) crossTabState.inFlight = null
    }
    const successor = followUp.expiredSuccessor
    if (successor && getSessionGeneration() === successor.generation &&
        authStore.token?.refreshToken === successor.token.refreshToken &&
        authStore.token?.accessToken === successor.token.accessToken) {
      return refreshToken()
    }
    return result
  }

  function initialize(): void {
    setupActivityRefresh()

    if (!authStore.token) {
      if (!restoreInFlight) {
        restoreInFlight = restoreRefreshSession({
          ensureDiscovery: loadDiscovery,
          fetchUserInfo,
          installSession: (nextToken, nextUser) => setToken(nextToken, nextUser),
        }).finally(() => {
          restoreInFlight = null
        })
      }
      void restoreInFlight
      return
    }

    if (Date.now() / 1000 >= authStore.token.expiresAt) {
      void refreshToken()
      return
    }

    scheduleRefreshTimer(authStore.token.expiresAt)
  }

  setupRefreshChannelListener()

  return {
    token,
    user,
    isAuthenticated,
    isTokenExpired,
    isLoading,
    error,
    loadDiscovery,
    getAuthorizationUrl: () => buildAuthorizationUrl(authorizationDeps),
    exchangeCodeForToken: (code: string) => runCodeExchange(authorizationDeps, code),
    refreshToken,
    logout,
    setToken,
    getSessionGeneration,
    initialize,
  }
}
