import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  clearRefreshTimer,
  clearTransientRetryTimer,
  getRefreshChannel,
  postRefreshMessage,
  scheduleRefreshTimer,
  scheduleTransientRetry,
  setupActivityRefresh,
  __resetSchedulerState,
  bindRefreshScheduler,
  ACTIVITY_CHECK_THROTTLE_MS,
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

describe('refreshScheduler', () => {
  beforeEach(() => {
    __resetSchedulerState()
    localStorage.clear()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('keeps the first bound callbacks — a second binding must not rewire armed timers', async () => {
    vi.useFakeTimers()
    const firstRefresh = vi.fn()
    bindRefreshScheduler({ onScheduledRefresh: firstRefresh, onActivityRefresh: vi.fn() })
    const secondRefresh = vi.fn()
    bindRefreshScheduler({ onScheduledRefresh: secondRefresh, onActivityRefresh: vi.fn() })
    scheduleRefreshTimer(Date.now() / 1000 + 100)
    await vi.advanceTimersByTimeAsync(200_000)
    expect(firstRefresh).toHaveBeenCalled()
    expect(secondRefresh).not.toHaveBeenCalled()
  })

  it('returns null when BroadcastChannel is unavailable', () => {
    vi.stubGlobal('BroadcastChannel', undefined)
    expect(getRefreshChannel()).toBeNull()
    expect(() => postRefreshMessage({ type: 'refresh-started', refreshToken: 'r' })).not.toThrow()
  })

  it('invokes the bound callback when the refresh timer fires', async () => {
    vi.useFakeTimers()
    const onScheduledRefresh = vi.fn()
    bindRefreshScheduler({ onScheduledRefresh, onActivityRefresh: vi.fn() })
    scheduleRefreshTimer(Date.now() / 1000 + 100)
    await vi.advanceTimersByTimeAsync(200_000)
    expect(onScheduledRefresh).toHaveBeenCalled()
  })

  it('is a no-op without a bound callback', async () => {
    vi.useFakeTimers()
    scheduleRefreshTimer(Date.now() / 1000 + 100)
    await expect(vi.advanceTimersByTimeAsync(200_000)).resolves.toBeDefined()
  })

  it('clears a pending refresh timer', () => {
    vi.useFakeTimers()
    const onScheduledRefresh = vi.fn()
    bindRefreshScheduler({ onScheduledRefresh, onActivityRefresh: vi.fn() })
    scheduleRefreshTimer(Date.now() / 1000 + 100)
    clearRefreshTimer()
    vi.advanceTimersByTime(200_000)
    expect(onScheduledRefresh).not.toHaveBeenCalled()
  })

  it('invokes the bound callback after the transient retry delay', async () => {
    vi.useFakeTimers()
    const onScheduledRefresh = vi.fn()
    bindRefreshScheduler({ onScheduledRefresh, onActivityRefresh: vi.fn() })
    scheduleTransientRetry(5_000)
    clearTransientRetryTimer()
    expect(onScheduledRefresh).not.toHaveBeenCalled()
    scheduleTransientRetry(5_000)
    await vi.advanceTimersByTimeAsync(5_000)
    expect(onScheduledRefresh).toHaveBeenCalledTimes(1)
  })

  it('throttles repeated activity events within the window', async () => {
    vi.useFakeTimers()
    const onActivityRefresh = vi.fn()
    bindRefreshScheduler({ onScheduledRefresh: vi.fn(), onActivityRefresh })
    setupActivityRefresh()
    document.dispatchEvent(new Event('mousemove'))
    document.dispatchEvent(new Event('keydown'))
    expect(onActivityRefresh).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(ACTIVITY_CHECK_THROTTLE_MS + 1)
    document.dispatchEvent(new Event('click'))
    expect(onActivityRefresh).toHaveBeenCalledTimes(2)
  })

  it('triggers activity refresh on visibilitychange and focus', async () => {
    vi.useFakeTimers()
    const onActivityRefresh = vi.fn()
    bindRefreshScheduler({ onScheduledRefresh: vi.fn(), onActivityRefresh })
    setupActivityRefresh()
    await vi.advanceTimersByTimeAsync(ACTIVITY_CHECK_THROTTLE_MS + 1)
    Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true })
    document.dispatchEvent(new Event('visibilitychange'))
    await vi.advanceTimersByTimeAsync(ACTIVITY_CHECK_THROTTLE_MS + 1)
    window.dispatchEvent(new Event('focus'))
    expect(onActivityRefresh).toHaveBeenCalledTimes(2)
  })

  it('ignores activity callbacks when none is bound', () => {
    setupActivityRefresh()
    expect(() => document.dispatchEvent(new Event('scroll'))).not.toThrow()
  })
})

describe('oidcSession', () => {
  beforeEach(() => {
    sessionStorage.clear()
    __resetSessionLifecycle()
  })

  it('advances the generation and notifies the bound host', () => {
    const host = { invalidateCrossTabState: vi.fn(), clearTimers: vi.fn(), scheduleRefresh: vi.fn() }
    bindSessionLifecycle(host)
    const before = getSessionGeneration()
    advanceSessionGeneration()
    expect(getSessionGeneration()).toBe(before + 1)
    expect(host.invalidateCrossTabState).toHaveBeenCalled()
    expect(host.clearTimers).toHaveBeenCalled()
  })

  it('keeps the first bound host — a second binding must not rewire live session state', () => {
    const firstHost = { invalidateCrossTabState: vi.fn(), clearTimers: vi.fn(), scheduleRefresh: vi.fn() }
    bindSessionLifecycle(firstHost)
    const secondHost = { invalidateCrossTabState: vi.fn(), clearTimers: vi.fn(), scheduleRefresh: vi.fn() }
    bindSessionLifecycle(secondHost)
    advanceSessionGeneration()
    expect(firstHost.invalidateCrossTabState).toHaveBeenCalled()
    expect(secondHost.invalidateCrossTabState).not.toHaveBeenCalled()
  })

  it('advances the generation and installs tokens before any host is bound', async () => {
    await vi.resetModules()
    const fresh = await import('./oidcSession')
    expect(() => fresh.advanceSessionGeneration()).not.toThrow()
    expect(fresh.getSessionGeneration()).toBe(1)
    const setAuth = vi.fn()
    fresh.installSessionToken(setAuth, null, null)
    expect(setAuth).toHaveBeenCalledWith(null, null)
  })

  it('tracks the latest refresh operation id', () => {
    const first = nextRefreshOperationId()
    const second = nextRefreshOperationId()
    expect(isLatestRefreshOperation(second)).toBe(true)
    expect(isLatestRefreshOperation(first)).toBe(false)
  })

  it('ends the local session with replay protection and navigation', () => {
    localStorage.setItem('oidc-refresh-result:x', JSON.stringify({ token: {}, user: null, recordedAt: 1 }))
    const clearAuth = vi.fn()
    const navigate = vi.fn()
    endLocalSession(clearAuth, navigate)
    expect(clearAuth).toHaveBeenCalled()
    expect(navigate).toHaveBeenCalled()
    expect(localStorage.getItem('oidc-refresh-result:x')).toBe('consumed')
  })

  it('installs a token and schedules its refresh', () => {
    const host = { invalidateCrossTabState: vi.fn(), clearTimers: vi.fn(), scheduleRefresh: vi.fn() }
    bindSessionLifecycle(host)
    const setAuth = vi.fn()
    const token = { accessToken: 'a', idToken: '', refreshToken: 'r', expiresAt: 1 }
    installSessionToken(setAuth, token, { sub: 's' })
    expect(setAuth).toHaveBeenCalledWith(token, { sub: 's' })
    expect(host.scheduleRefresh).toHaveBeenCalledWith(token)
  })

  it('clears PKCE session artifacts', () => {
    sessionStorage.setItem('oidc_code_verifier', 'v')
    sessionStorage.setItem('oidc_state', 's')
    clearLocalArtifacts()
    expect(sessionStorage.getItem('oidc_code_verifier')).toBeNull()
    expect(sessionStorage.getItem('oidc_state')).toBeNull()
  })
})
