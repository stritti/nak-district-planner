import { computed, ref } from 'vue'
import { useRouter, type Router } from 'vue-router'
import { useAuthStore } from '../stores/auth'

export interface OIDCToken {
  accessToken: string
  idToken: string
  refreshToken?: string
  expiresAt: number
}

export interface OIDCUser {
  sub: string
  email?: string
  name?: string
  picture?: string
}

export interface OIDCDiscovery {
  authorization_endpoint: string
  token_endpoint: string
  userinfo_endpoint?: string
  revocation_endpoint?: string
  end_session_endpoint?: string
  jwks_uri?: string
  /** Added by backend proxy — the OIDC client ID for this application */
  client_id?: string
}

export interface OIDCConfig {
  redirectUri: string
  scope: string
}

const SESSION_CODE_VERIFIER_KEY = 'oidc_code_verifier'
const SESSION_STATE_KEY = 'oidc_state'

// Refresh eagerly if user activity is detected while the token is within this
// many seconds of expiry. Catches cases where the scheduled setTimeout-based
// refresh was throttled or paused (backgrounded tab, device sleep) so the
// session gets extended as soon as the user resumes working.
const ACTIVITY_REFRESH_LEAD_SECONDS = 120
// Don't re-check on every single event — throttle to avoid excessive work.
const ACTIVITY_CHECK_THROTTLE_MS = 15_000
const REFRESH_TIMEOUT_MS = 35_000
const REFRESH_CHANNEL = 'oidc-refresh'
const CROSS_TAB_WAIT_TIMEOUT_MS = 40_000
const ROTATED_TOKEN_TTL_MS = 60_000
const PERSISTED_RECEIPT_TTL_MS = 24 * 60 * 60 * 1000
const MAX_PERSISTED_RECEIPTS = 32
const MAX_RECEIPT_CHAIN_LENGTH = 64
const TRANSIENT_RETRY_DELAY_MS = 30_000

// Module-level guards: listeners must only be attached once per page load,
// regardless of how many times useOIDC() is instantiated across the app.
let activityListenersAttached = false
let lastActivityCheckAt = 0
let refreshInFlight: Promise<boolean> | null = null
let refreshInFlightId = 0
let sessionGeneration = 0
let refreshTimer: ReturnType<typeof setTimeout> | null = null
let transientRetryTimer: ReturnType<typeof setTimeout> | null = null
let refreshChannel: BroadcastChannel | null = null
let refreshChannelListenerAttached = false
let lastAdoptedBroadcastAt = 0
let crossTabWaiter:
  | { refreshToken: string; resolve: (ok: boolean) => void; timeoutId: ReturnType<typeof setTimeout> }
  | null = null
const rotatedTokens = new Map<
  string,
  { token: OIDCToken; user: OIDCUser | null; recordedAt: number }
>()

type RefreshChannelMessage =
  | { type: 'refresh-started'; refreshToken: string }
  | { type: 'refresh-complete'; ok: boolean; refreshToken: string; token?: OIDCToken; user?: OIDCUser | null; completedAt?: number }

const envConfig: OIDCConfig = {
  redirectUri: `${window.location.origin}/auth/callback`,
  scope: import.meta.env.VITE_OIDC_SCOPE || 'openid profile email',
}

function toBase64Url(bytes: Uint8Array): string {
  const binary = Array.from(bytes, (byte) => String.fromCharCode(byte)).join('')
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '')
}

function generateCodeVerifier(): string {
  const bytes = new Uint8Array(96)
  crypto.getRandomValues(bytes)
  return toBase64Url(bytes)
}

async function generateCodeChallenge(verifier: string): Promise<string> {
  const data = new TextEncoder().encode(verifier)
  const digest = await crypto.subtle.digest('SHA-256', data)
  return toBase64Url(new Uint8Array(digest))
}

function generateState(): string {
  const bytes = new Uint8Array(32)
  crypto.getRandomValues(bytes)
  return toBase64Url(bytes)
}

async function rotationReceiptKey(refreshToken: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(refreshToken))
  return 'oidc-refresh-result:' + toBase64Url(new Uint8Array(digest))
}

function validReceiptToken(value: unknown): value is OIDCToken {
  if (!value || typeof value !== 'object') return false
  const token = value as Partial<OIDCToken>
  return typeof token.accessToken === 'string' && token.accessToken.length > 0 &&
    typeof token.refreshToken === 'string' && token.refreshToken.length > 0 &&
    typeof token.idToken === 'string' &&
    typeof token.expiresAt === 'number' && Number.isFinite(token.expiresAt)
}

function prunePersistedReceipts(): void {
  const now = Date.now()
  const completed: { key: string; recordedAt: number }[] = []
  for (let i = 0; i < localStorage.length; i += 1) {
    const key = localStorage.key(i)
    if (!key?.startsWith('oidc-refresh-result:')) continue
    const raw = localStorage.getItem(key)
    if (!raw || raw === 'consumed') continue // Retain pending markers and replay tombstones.
    try {
      const receipt = JSON.parse(raw) as { recordedAt?: number }
      const recordedAt = receipt.recordedAt
      if (typeof recordedAt !== 'number' || !Number.isFinite(recordedAt) ||
          recordedAt > now || now - recordedAt > PERSISTED_RECEIPT_TTL_MS) {
        localStorage.setItem(key, 'consumed') // Non-secret replay tombstone for suspended tabs.
      } else completed.push({ key, recordedAt })
    } catch {
      // Malformed receipts are handled by fail-closed adoption, not pruning.
    }
  }
  completed.sort((a, b) => b.recordedAt - a.recordedAt)
  for (const entry of completed.slice(MAX_PERSISTED_RECEIPTS)) {
    localStorage.setItem(entry.key, 'consumed')
  }
}

function parseJwt(token: string): Record<string, unknown> {
  try {
    const base64Url = token.split('.')[1]
    if (!base64Url) return {}
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const padding = '='.repeat((4 - (base64.length % 4)) % 4)
    return JSON.parse(atob(base64 + padding)) as Record<string, unknown>
  } catch {
    return {}
  }
}

function getRefreshChannel(): BroadcastChannel | null {
  if (typeof BroadcastChannel === 'undefined') return null
  if (!refreshChannel) refreshChannel = new BroadcastChannel(REFRESH_CHANNEL)
  return refreshChannel
}

function clearCrossTabWaiter(resolveWith = false): void {
  if (!crossTabWaiter) return
  clearTimeout(crossTabWaiter.timeoutId)
  const resolve = crossTabWaiter.resolve
  crossTabWaiter = null
  resolve(resolveWith)
}

function waitForCrossTabRefresh(refreshToken: string): Promise<boolean> {
  return new Promise<boolean>((resolve) => {
    const timeoutId = setTimeout(() => {
      if (crossTabWaiter?.refreshToken === refreshToken) {
        crossTabWaiter = null
        refreshInFlight = null
        resolve(false)
      }
    }, CROSS_TAB_WAIT_TIMEOUT_MS)
    crossTabWaiter = { refreshToken, resolve, timeoutId }
  })
}

function pruneRotatedTokens(now = Date.now()): void {
  for (const [refreshToken, entry] of rotatedTokens.entries()) {
    if (now - entry.recordedAt > ROTATED_TOKEN_TTL_MS) rotatedTokens.delete(refreshToken)
  }
}

function postRefreshMessage(message: RefreshChannelMessage): void {
  try {
    getRefreshChannel()?.postMessage(message)
  } catch {
    // BroadcastChannel failures must never break local refresh/session flow.
  }
}

type ReceiptClaim = 'proceed' | 'stop' | 'adopt'

interface LockOwnerContext {
  receiptKey: string
  isRefreshStillCurrent: () => boolean
  inspectStoredReceipt: () => Promise<ReceiptClaim>
  adoptLatestReceipt: () => Promise<boolean>
  runRefreshBody: () => Promise<boolean>
  persistRefreshOutcome: (ok: boolean) => boolean
}

// Phases run while holding the Web Lock: decide whether the captured
// refresh token may be submitted, then persist the outcome for the next
// lock owner. Kept as a named function so each phase reads in isolation.
async function runLockOwnerPhases(context: LockOwnerContext): Promise<boolean> {
  const claim = await context.inspectStoredReceipt()
  if (claim === 'adopt') return await context.adoptLatestReceipt()
  if (claim === 'stop') return false
  if (!context.isRefreshStillCurrent()) {
    try {
      if (localStorage.getItem(context.receiptKey) === '') localStorage.removeItem(context.receiptKey)
    } catch { /* fail closed */ }
    return false
  }
  return context.persistRefreshOutcome(await context.runRefreshBody())
}

interface LockedRefreshContext extends LockOwnerContext {
  refreshTokenUsed: string
  waitForCrossTabRefresh: (refreshToken: string) => Promise<boolean>
  hasFreshAdoptedToken: () => boolean
}

// Serialize the refresh across tabs: either acquire the Web Lock and run
// the owner phases, or yield to the current owner and adopt its result.
async function runLockedRefresh(context: LockedRefreshContext): Promise<boolean> {
  return navigator.locks.request(`oidc-refresh:${context.refreshTokenUsed}`, { ifAvailable: true }, async (lock) => {
    if (!lock) {
      const received = await context.waitForCrossTabRefresh(context.refreshTokenUsed)
      if (received && context.hasFreshAdoptedToken()) return true
      return await context.adoptLatestReceipt()
    }
    return await runLockOwnerPhases(context)
  })
}

/** @internal — resets module-level state; used by tests */
export function __resetOIDCModuleState(): void {
  refreshInFlight = null
  refreshInFlightId = 0
  sessionGeneration = 0
  if (refreshTimer) clearTimeout(refreshTimer)
  refreshTimer = null
  if (transientRetryTimer) clearTimeout(transientRetryTimer)
  transientRetryTimer = null
  if (crossTabWaiter) clearTimeout(crossTabWaiter.timeoutId)
  crossTabWaiter = null
  rotatedTokens.clear()
  refreshChannel?.close()
  refreshChannel = null
  refreshChannelListenerAttached = false
  lastAdoptedBroadcastAt = 0
  activityListenersAttached = false
  lastActivityCheckAt = 0
}

export function useOIDC(router?: Router, config?: Partial<OIDCConfig>) {
  let injectedRouter: Router | null = router || null
  const authStore = useAuthStore()
  const oidcConfig: OIDCConfig = { ...envConfig, ...(config || {}) }
  setupRefreshChannelListener()

  const discovery = ref<OIDCDiscovery | null>(null)
  const clientId = ref<string>('')
  const discoveryPromise = ref<Promise<void> | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
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

  function clearLocalArtifacts(): void {
    sessionStorage.removeItem(SESSION_CODE_VERIFIER_KEY)
    sessionStorage.removeItem(SESSION_STATE_KEY)
  }

  async function fetchUserInfo(accessToken: string): Promise<OIDCUser | null> {
    const endpoint = discovery.value?.userinfo_endpoint
    if (!endpoint) return null

    const response = await fetch(endpoint, {
      headers: { Authorization: `Bearer ${accessToken}` },
    })

    if (!response.ok) return null

    const data = await response.json()
    if (!data.sub) return null

    return {
      sub: data.sub,
      email: data.email,
      name: data.name,
      picture: data.picture,
    }
  }

  function scheduleTransientRefreshRetry(): void {
    const current = authStore.token
    if (!current) return
    if (transientRetryTimer) clearTimeout(transientRetryTimer)
    transientRetryTimer = null

    if (Date.now() / 1000 < current.expiresAt) {
      setupRefreshTimer()
      return
    }

    transientRetryTimer = setTimeout(() => {
      transientRetryTimer = null
      void refreshToken()
    }, TRANSIENT_RETRY_DELAY_MS)
  }

  function adoptRotatedToken(token: OIDCToken, nextUser: OIDCUser | null): void {
    if (transientRetryTimer) clearTimeout(transientRetryTimer)
    transientRetryTimer = null
    authStore.setToken(token, nextUser ?? authStore.user)
    setupRefreshTimer()
  }

  function setupRefreshChannelListener(): void {
    if (refreshChannelListenerAttached) return
    const channel = getRefreshChannel()
    if (!channel) return
    refreshChannelListenerAttached = true

    channel.onmessage = (event: MessageEvent<RefreshChannelMessage>) => {
      const message = event.data
      const currentRefreshToken = authStore.token?.refreshToken
      if (!currentRefreshToken || message.refreshToken !== currentRefreshToken) return

      if (message.type === 'refresh-started') {
        if (refreshInFlight) return
        refreshInFlight = waitForCrossTabRefresh(message.refreshToken)
        return
      }

      if (message.ok && message.token) {
        // BroadcastChannel does not totally order messages across senders.
        // With a non-rotating refresh token every completion carries the same
        // refreshToken, so a delayed older completion must not roll the
        // session back to an expired or revoked bearer.
        const completedAt = typeof message.completedAt === 'number' ? message.completedAt : Date.now()
        if (completedAt < lastAdoptedBroadcastAt) return
        lastAdoptedBroadcastAt = completedAt
        rotatedTokens.set(message.refreshToken, {
          token: message.token,
          user: message.user ?? authStore.user,
          recordedAt: completedAt,
        })
        pruneRotatedTokens()
        adoptRotatedToken(message.token, message.user ?? authStore.user)
        clearCrossTabWaiter(true)
      } else {
        clearCrossTabWaiter(false)
      }
      refreshInFlight = null
    }
  }

  async function loadDiscovery(): Promise<void> {
    if (discovery.value) return
    if (discoveryPromise.value) return discoveryPromise.value

    const promise = (async () => {
      isLoading.value = true
      error.value = null

      try {
        // Fetch discovery document from backend proxy (avoids CORS + build-time env)
        const response = await fetch('/api/v1/auth/oidc/discovery')
        if (!response.ok) {
          const body = await response.text().catch(() => '')
          throw new Error(`OIDC discovery failed (${response.status}): ${body}`)
        }

        const data = (await response.json()) as OIDCDiscovery
        if (!data.authorization_endpoint || !data.token_endpoint) {
          throw new Error('OIDC discovery document misses required endpoints')
        }

        discovery.value = data
        // client_id is provided by the backend alongside the discovery doc
        if (data.client_id) {
          clientId.value = data.client_id
        } else {
          throw new Error('OIDC client ID not provided by backend')
        }
      } catch (err) {
        error.value = err instanceof Error ? err.message : 'Discovery failed'
        throw err
      } finally {
        isLoading.value = false
      }
    })()

    discoveryPromise.value = promise
    try {
      await promise
    } finally {
      discoveryPromise.value = null
    }
  }

  async function getAuthorizationUrl(): Promise<string> {
    await loadDiscovery()
    if (!discovery.value) throw new Error('Discovery not loaded')

    const codeVerifier = generateCodeVerifier()
    const codeChallenge = await generateCodeChallenge(codeVerifier)
    const state = generateState()

    sessionStorage.setItem(SESSION_CODE_VERIFIER_KEY, codeVerifier)
    sessionStorage.setItem(SESSION_STATE_KEY, state)

    const params = new URLSearchParams({
      client_id: clientId.value,
      redirect_uri: oidcConfig.redirectUri,
      response_type: 'code',
      scope: oidcConfig.scope,
      code_challenge: codeChallenge,
      code_challenge_method: 'S256',
      state,
    })

    return `${discovery.value.authorization_endpoint}?${params.toString()}`
  }

  async function exchangeCodeForToken(code: string): Promise<void> {
    await loadDiscovery()
    if (!discovery.value) throw new Error('Discovery not loaded')

    const codeVerifier = sessionStorage.getItem(SESSION_CODE_VERIFIER_KEY)
    if (!codeVerifier) throw new Error('Code verifier not found in session storage')

    isLoading.value = true
    error.value = null

    try {
      // Send code + PKCE verifier to backend proxy; backend adds client_secret
      const response = await fetch('/api/v1/auth/oidc/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          grant_type: 'authorization_code',
          code,
          redirect_uri: oidcConfig.redirectUri,
          code_verifier: codeVerifier,
        }),
      })

      if (!response.ok) {
        const raw = await response.text()
        let parsed: unknown = raw
        try {
          parsed = JSON.parse(raw)
        } catch {
          // keep raw text
        }
        throw new Error(`Token exchange failed (${response.status}): ${JSON.stringify(parsed)}`)
      }

      const data = await response.json()
      if (!data.access_token) throw new Error('Token response missing access_token')

      const claims = parseJwt((data.id_token as string) || (data.access_token as string))
      const nextToken: OIDCToken = {
        accessToken: data.access_token,
        idToken: data.id_token || '',
        refreshToken: data.refresh_token,
        expiresAt: Math.floor(Date.now() / 1000) + Number(data.expires_in || 3600),
      }

      let nextUser: OIDCUser | null = {
        sub: (claims.sub as string) || '',
        email: (claims.email as string) || undefined,
        name: (claims.name as string) || undefined,
        picture: (claims.picture as string) || undefined,
      }

      if (!nextUser.sub) {
        nextUser = await fetchUserInfo(nextToken.accessToken)
      }

      if (!nextUser?.sub) {
        throw new Error('OIDC identity missing: no sub in id_token/access_token or userinfo response')
      }

      setToken(nextToken, nextUser)
      clearLocalArtifacts()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Token exchange failed'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function refreshToken(): Promise<boolean> {
    if (refreshInFlight) return refreshInFlight

    // An expired successor is adopted first, then refreshed in a new locked
    // operation after the current operation has released its lock.
    const followUp: { expiredSuccessor?: { token: OIDCToken; generation: number } } = {}
    const operation: Promise<boolean> = (async () => {
      const current = authStore.token
      if (!current?.refreshToken) {
        await logout()
        return false
      }
      const refreshGeneration = sessionGeneration
      const refreshTokenUsed = current.refreshToken
      const isRefreshStillCurrent = (): boolean => {
        const latest = authStore.token
        return (
          refreshGeneration === sessionGeneration &&
          Boolean(latest) &&
          latest?.refreshToken === refreshTokenUsed
        )
      }
      const logoutIfRefreshStillCurrent = (): void => {
        pruneRotatedTokens()
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
        // Only a definitive pre-provider rejection permits reusing the token.
        // Transport errors, timeouts and malformed responses are ambiguous.
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

          const data = await response.json()
          if (!data.access_token) {
            return false
          }

          const claims = parseJwt((data.id_token as string) || (data.access_token as string))
          let nextUser: OIDCUser | null = authStore.user

          if (claims.sub) {
            nextUser = {
              sub: claims.sub as string,
              email: (claims.email as string) || authStore.user?.email,
              name: (claims.name as string) || authStore.user?.name,
              picture: (claims.picture as string) || authStore.user?.picture,
            }
          } else if (!authStore.user?.sub) {
            nextUser = await fetchUserInfo(data.access_token)
          }

          if (!nextUser?.sub) {
            logoutIfRefreshStillCurrent()
            return false
          }

          if (!isRefreshStillCurrent()) return false

          const nextToken: OIDCToken = {
            accessToken: data.access_token,
            idToken: data.id_token || current.idToken,
            refreshToken: data.refresh_token || current.refreshToken,
            expiresAt: Math.floor(Date.now() / 1000) + Number(data.expires_in || 3600),
          }

          authStore.setToken(nextToken, nextUser)
          if (transientRetryTimer) clearTimeout(transientRetryTimer)
          transientRetryTimer = null
          rotatedTokens.set(refreshTokenUsed, { token: nextToken, user: nextUser, recordedAt: Date.now() })
          pruneRotatedTokens()
          completedOk = true
          completedToken = nextToken
          completedUser = nextUser
          setupRefreshTimer()
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

      // localStorage read/write is not atomic across tabs, so no lease or
      // ownership check can safely serialize rotating refresh tokens.
      if (typeof navigator === 'undefined' || !navigator.locks) {
        // localStorage read/write is not atomic across tabs. A delay or
        // ownership recheck cannot safely serialize rotating refresh tokens.
        // Fail closed when Web Locks is unavailable rather than risk token
        // reuse (and possible revocation of the entire token family).
        // Do not retry automatically: this browser cannot acquire a safe lock.
        // Keep a still-valid access token until expiry, then clear auth.
        if (current.expiresAt <= Date.now() / 1000 && isRefreshStillCurrent()) {
          void logout()
        } else if (isRefreshStillCurrent()) {
          setTimeout(() => {
            if (isRefreshStillCurrent() && current.expiresAt <= Date.now() / 1000) void logout()
          }, Math.max(0, current.expiresAt * 1000 - Date.now()))
        }
        return false
      }

      // A lock serializes network requests, but a waiting tab may acquire it
      // before its BroadcastChannel receives the preceding tab's rotation.
      // Persist the rotation receipt while still holding the lock; the next
      // owner must consult it before submitting the captured refresh token.
      const receiptKey = await rotationReceiptKey(refreshTokenUsed)
      // End the local session while preserving the non-secret replay markers
      // that suspended tabs rely on for token-replay protection.
      const endLocalSession = (): void => {
        invalidateSession()
        // Completed receipts still hold the raw refresh token that was just
        // submitted; a failure before reaching the provider leaves it usable.
        clearRotationReceipts()
        authStore.clearAuth()
        try { void getRouter().push('/login').catch(() => {}) } catch { /* Router unavailable during startup. */ }
      }
      const failClosed = (): void => {
        if (!isRefreshStillCurrent()) return
        endLocalSession()
      }
      const adoptLatestReceipt = async (): Promise<boolean> => {
        if (!isRefreshStillCurrent()) return false
        let next = refreshTokenUsed
        const seen = new Set<string>()
        let latest: { token: OIDCToken; user: OIDCUser | null } | null = null
        try {
          while (!seen.has(next) && seen.size < MAX_RECEIPT_CHAIN_LENGTH) {
            seen.add(next)
            const raw = localStorage.getItem(await rotationReceiptKey(next))
            if (!raw) break
            if (raw === 'consumed') throw new Error('Refresh token was already consumed; receipt compacted')
            const receipt = JSON.parse(raw) as { token: OIDCToken; user: OIDCUser | null }
            if (!validReceiptToken(receipt.token)) throw new Error('Invalid persisted rotation receipt')
            latest = receipt
            if (receipt.token.refreshToken === next) break // Non-rotating provider.
            next = receipt.token.refreshToken!
          }
        } catch {
          failClosed()
          return false
        }
        if (!latest || !isRefreshStillCurrent()) return false
        adoptRotatedToken(latest.token, latest.user)
        // Never report success with an expired bearer token.
        if (latest.token.expiresAt <= Date.now() / 1000) {
          followUp.expiredSuccessor = { token: latest.token, generation: sessionGeneration }
          return false
        }
        return true
      }
      // Decide under the Web Lock whether the captured refresh token may be
      // submitted, has an adoptable successor, or must not be replayed.
      const inspectStoredReceipt = async (): Promise<ReceiptClaim> => {
        try {
          const raw = localStorage.getItem(receiptKey)
          if (raw === 'consumed') {
            failClosed() // The token was rotated before this tab was suspended.
            return 'stop'
          }
          if (raw === '') {
            // The previous owner may have crashed after submitting a rotating
            // token. Preserve the marker across local logout.
            if (isRefreshStillCurrent()) void logout()
            return 'stop'
          }
          if (raw) {
            const receipt = JSON.parse(raw) as {
              token: OIDCToken; user: OIDCUser | null; recordedAt: number
            }
            if (!validReceiptToken(receipt.token)) {
              failClosed()
              return 'stop'
            }
            if (receipt.token.refreshToken === refreshTokenUsed &&
                (receipt.token.accessToken === current.accessToken || receipt.token.expiresAt <= Date.now() / 1000)) {
              // A stable refresh token may be reused after the previous
              // completed receipt has been consumed. This check and removal
              // happen exclusively under the Web Lock.
              localStorage.removeItem(receiptKey)
              localStorage.setItem(receiptKey, '') // Protect the next request, even if it rotates.
            } else {
              return 'adopt'
            }
          }
          // Shared storage is required to communicate rotation to the next
          // lock owner; without it we cannot safely refresh across tabs.
          if (localStorage.getItem(receiptKey) === null) {
            prunePersistedReceipts()
            localStorage.setItem(receiptKey, '')
          }
          return 'proceed'
        } catch {
          failClosed()
          return 'stop'
        }
      }
      // Persist the outcome for the next lock owner and, on ambiguous
      // failures, end the local session without enabling token replay.
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
              if (authStore.token?.refreshToken === rotated.token.refreshToken && authStore.token?.accessToken === rotated.token.accessToken) {
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
            if (localStorage.getItem(receiptKey) === '') localStorage.removeItem(receiptKey)
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
      return runLockedRefresh({
        receiptKey,
        refreshTokenUsed,
        isRefreshStillCurrent,
        inspectStoredReceipt,
        adoptLatestReceipt,
        runRefreshBody,
        persistRefreshOutcome,
        waitForCrossTabRefresh,
        hasFreshAdoptedToken: () => {
          const token = authStore.token
          return token !== null && token.expiresAt > Date.now() / 1000
        },
      })
    })()

    const operationId = refreshInFlightId + 1
    refreshInFlightId = operationId
    refreshInFlight = operation
    let result: boolean
    try {
      result = await operation
    } finally {
      if (refreshInFlightId === operationId) refreshInFlight = null
    }
    // The new token must acquire its own Web Lock and check its own receipt.
    // Never refresh if a login/logout replaced the adopted session meanwhile.
    const successor = followUp.expiredSuccessor
    if (successor && sessionGeneration === successor.generation &&
        authStore.token?.refreshToken === successor.token.refreshToken &&
        authStore.token?.accessToken === successor.token.accessToken) {
      return refreshToken()
    }
    return result
  }

  function setupRefreshTimer(): void {
    if (refreshTimer) clearTimeout(refreshTimer)
    refreshTimer = null
    if (!authStore.token) return

    const nowSeconds = Date.now() / 1000
    const ttlSeconds = Math.max(authStore.token.expiresAt - nowSeconds, 0)

    // Avoid refresh loops for short-lived tokens.
    // Refresh at ~80% of lifetime with sane bounds.
    const refreshLeadSeconds = Math.min(300, Math.max(5, Math.floor(ttlSeconds * 0.2)))
    const delay = Math.max((ttlSeconds - refreshLeadSeconds) * 1000, 1000)

    refreshTimer = setTimeout(() => {
      void refreshToken()
    }, delay)
  }

  function invalidateSession(): void {
    sessionGeneration += 1
    refreshInFlightId += 1
    refreshInFlight = null
    clearCrossTabWaiter(false)
    if (refreshTimer) clearTimeout(refreshTimer)
    refreshTimer = null
    if (transientRetryTimer) clearTimeout(transientRetryTimer)
    transientRetryTimer = null
  }

  function clearRotationReceipts(): void {
    try {
      const keys: string[] = []
      for (let i = 0; i < localStorage.length; i += 1) {
        const key = localStorage.key(i)
        // Keep both ambiguous pending markers and non-secret consumed-token
        // tombstones: suspended tabs must never replay a rotated credential.
        if (key?.startsWith('oidc-refresh-result:') &&
            localStorage.getItem(key) !== '' && localStorage.getItem(key) !== 'consumed') keys.push(key)
      }
      keys.forEach((key) => localStorage.setItem(key, 'consumed'))
    } catch { /* Storage may be unavailable. */ }
  }

  async function logout(): Promise<void> {
    const current = authStore.token
    invalidateSession()
    clearRotationReceipts()
    clearLocalArtifacts()
    authStore.clearAuth()
    // Local logout is immediate. Discovery/revocation are best effort and
    // must never hold the shared refresh promise hostage.

    try {
      await Promise.race([loadDiscovery(), new Promise<void>((resolve) => setTimeout(resolve, 2_000))]).catch(() => {
        // best effort
      })

      const revocationEndpoint = discovery.value?.revocation_endpoint
      if (current && revocationEndpoint) {
        const body = new URLSearchParams({
          client_id: clientId.value,
          token: current.refreshToken || current.accessToken,
        })

        await fetch(revocationEndpoint, {
          method: 'POST',
          signal: AbortSignal.timeout(2_000),
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: body.toString(),
        }).catch(() => {
          // ignore remote logout errors
        })
      }
    } finally {
      try {
        await getRouter().push('/login')
      } catch {
        // router can be unavailable during startup/tests
      }
    }
  }

  function setToken(nextToken: OIDCToken | null, nextUser: OIDCUser | null = null): void {
    // invalidateSession() already advanced the generation; installing the
    // new token must not advance it again — the refresh pipeline treats the
    // post-invalidation generation as the new session's identity.
    invalidateSession()
    clearRotationReceipts()
    authStore.setToken(nextToken, nextUser)
    if (nextToken) {
      setupRefreshTimer()
    }
  }

  function handleUserActivity(): void {
    const now = Date.now()
    if (now - lastActivityCheckAt < ACTIVITY_CHECK_THROTTLE_MS) return
    lastActivityCheckAt = now

    const current = authStore.token
    if (!current || refreshInFlight) return

    const secondsUntilExpiry = current.expiresAt - now / 1000
    if (secondsUntilExpiry < ACTIVITY_REFRESH_LEAD_SECONDS) {
      void refreshToken()
    }
  }

  // Attach once, app-wide: browsers throttle/suspend setTimeout in background
  // tabs, so user interaction is used as a second trigger to keep the
  // session alive whenever the token is close to (or past) expiry.
  function setupActivityRefresh(): void {
    if (activityListenersAttached) return
    activityListenersAttached = true

    const activityEvents = ['mousemove', 'keydown', 'click', 'touchstart', 'scroll']
    activityEvents.forEach((eventName) => {
      document.addEventListener(eventName, handleUserActivity, { passive: true })
    })
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') handleUserActivity()
    })
    window.addEventListener('focus', handleUserActivity)
  }

  function initialize(): void {
    setupActivityRefresh()

    if (!authStore.token) return

    if (Date.now() / 1000 >= authStore.token.expiresAt) {
      void refreshToken()
      return
    }

    setupRefreshTimer()
  }

  return {
    token,
    user,
    isAuthenticated,
    isTokenExpired,
    isLoading,
    error,
    loadDiscovery,
    getAuthorizationUrl,
    exchangeCodeForToken,
    refreshToken,
    logout,
    setToken,
    getSessionGeneration: () => sessionGeneration,
    initialize,
  }
}
