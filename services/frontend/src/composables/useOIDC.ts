import { computed } from 'vue'
import { useRouter, type Router } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import type { OIDCConfig, OIDCToken, OIDCUser } from './oidcTypes'
import { isValidTokenShape } from './oidcToken'
import {
  clearCrossTabWaiter as clearWaiter,
  type CrossTabRefreshState,
  type RefreshChannelMessage,
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
import { getCurrentCSRFHeaders } from './useCSRF'

export type { OIDCConfig, OIDCDiscovery, OIDCToken, OIDCUser } from './oidcTypes'

const envConfig: OIDCConfig = {
  redirectUri: `${window.location.origin}/auth/callback`,
  scope: import.meta.env.VITE_OIDC_SCOPE || 'openid profile email',
}

// Module-level refresh coordination is shared by all composable instances.
// It contains no provider credential and is never persisted.
let lastAdoptedBroadcastAt = 0
const crossTabState: CrossTabRefreshState = { inFlight: null, waiter: null }
let restoreInFlight: Promise<boolean> | null = null

/** @internal — resets module-level state; used by tests */
export function __resetOIDCModuleState(): void {
  crossTabState.inFlight = null
  if (crossTabState.waiter) clearTimeout(crossTabState.waiter.timeoutId)
  crossTabState.waiter = null
  restoreInFlight = null
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

  function scheduleRefreshFor(currentToken: OIDCToken | null): void {
    if (currentToken) scheduleRefreshTimer(currentToken.expiresAt)
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

  function adoptRefreshedToken(nextToken: OIDCToken, nextUser: OIDCUser | null): void {
    clearTransientRetryTimer()
    authStore.setToken(nextToken, nextUser ?? authStore.user)
    scheduleRefreshTimer(nextToken.expiresAt)
  }

  function navigateToLogin(): void {
    try { void getRouter().push('/login').catch(() => {}) } catch { /* Router unavailable during startup. */ }
  }

  function setToken(nextToken: OIDCToken | null, nextUser: OIDCUser | null = null): void {
    advanceSessionGeneration()
    installSessionToken((next, nextIdentity) => authStore.setToken(next, nextIdentity), nextToken, nextUser)
  }

  /** Restore the memory-only session once before protected navigation is decided. */
  async function ensureSession(): Promise<boolean> {
    if (authStore.token) return true
    if (!restoreInFlight) {
      restoreInFlight = restoreRefreshSession({
        ensureDiscovery: loadDiscovery,
        fetchUserInfo,
        installSession: (nextToken, nextUser) => setToken(nextToken, nextUser),
      }).finally(() => {
        restoreInFlight = null
      })
    }
    return await restoreInFlight
  }

  async function logout(): Promise<void> {
    advanceSessionGeneration()
    clearLocalArtifacts()
    authStore.clearAuth()

    // Local logout is immediate. Provider revocation is a cookie-backed,
    // CSRF-protected best-effort backend operation.
    try {
      await fetch('/api/v1/auth/oidc/revoke', {
        method: 'POST',
        headers: getCurrentCSRFHeaders(),
        signal: AbortSignal.timeout(2_000),
      }).catch(() => {
        // Remote logout failure must not resurrect local authentication.
      })
    } finally {
      try {
        await getRouter().push('/login')
      } catch {
        // Router can be unavailable during startup/tests.
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
      const currentSessionId = authStore.token?.refreshToken
      if (!currentSessionId || message.sessionId !== currentSessionId) return

      if (message.type === 'refresh-started') {
        if (crossTabState.inFlight) return
        crossTabState.inFlight = waitForCrossTabRefresh(crossTabState, message.sessionId)
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
        adoptRefreshedToken(message.token, message.user ?? authStore.user)
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

    const operation: Promise<boolean> = (async () => {
      const current = authStore.token
      // Nothing to refresh while signed out. A full logout here would also wipe
      // the PKCE verifier/state of a login that is still in flight.
      if (!current) return false
      if (!current.refreshToken) {
        await logout()
        return false
      }

      const refreshGeneration = getSessionGeneration()
      const sessionId = current.refreshToken
      const isRefreshStillCurrent = (): boolean => {
        const latest = authStore.token
        return (
          refreshGeneration === getSessionGeneration() &&
          Boolean(latest) &&
          latest?.refreshToken === sessionId
        )
      }

      // Without Web Locks two tabs could send the same rotating provider
      // credential concurrently before the browser receives the updated
      // HttpOnly cookie. Keep a valid access token until expiry, then log out.
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
        sessionId,
        authStoreUser: () => authStore.user,
        fetchUserInfo,
        isRefreshStillCurrent,
        logout,
        adoptRefreshedToken,
        scheduleTransientRefreshRetry: () => {
          const latest = authStore.token
          if (!latest) return
          if (Date.now() / 1000 < latest.expiresAt) {
            scheduleRefreshTimer(latest.expiresAt)
            return
          }
          scheduleTransientRetry(TRANSIENT_RETRY_DELAY_MS)
        },
        endLocalSession: () => {
          endLocalSession(() => authStore.clearAuth(), navigateToLogin)
        },
        crossTabState,
        postRefreshMessage,
      })
    })()

    const operationId = nextRefreshOperationId()
    crossTabState.inFlight = operation
    try {
      return await operation
    } finally {
      if (isLatestRefreshOperation(operationId)) crossTabState.inFlight = null
    }
  }

  function initialize(): void {
    setupActivityRefresh()

    if (!authStore.token) {
      void ensureSession()
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
    ensureSession,
    getSessionGeneration,
    initialize,
  }
}
