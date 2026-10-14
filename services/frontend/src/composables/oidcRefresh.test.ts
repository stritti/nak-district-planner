// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  clearCrossTabWaiter,
  CROSS_TAB_WAIT_TIMEOUT_MS,
  runRefreshOperation,
  waitForCrossTabRefresh,
  type CrossTabRefreshState,
} from './oidcRefresh'
import { REFRESH_SESSION_COORDINATION_ID } from './oidcToken'
import type { OIDCToken, OIDCUser } from './oidcTypes'

const currentToken: OIDCToken = {
  accessToken: 'current-access',
  idToken: '',
  refreshToken: REFRESH_SESSION_COORDINATION_ID,
  expiresAt: 1_800_000_000,
}

const currentUser: OIDCUser = { sub: 'user-sub', email: 'user@example.org' }

function state(): CrossTabRefreshState {
  return { inFlight: null, waiter: null }
}

function grantLock(): void {
  vi.stubGlobal('navigator', {
    ...navigator,
    locks: {
      request: async (
        _name: string,
        _options: { ifAvailable: boolean },
        callback: (lock: Lock | null) => Promise<boolean>,
      ) => callback({ name: _name, mode: 'exclusive' } as Lock),
    },
  })
}

function denyLock(): void {
  vi.stubGlobal('navigator', {
    ...navigator,
    locks: {
      request: async (
        _name: string,
        _options: { ifAvailable: boolean },
        callback: (lock: Lock | null) => Promise<boolean>,
      ) => callback(null),
    },
  })
}

function response(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function options(overrides: Partial<Parameters<typeof runRefreshOperation>[0]> = {}) {
  return {
    currentToken,
    sessionId: REFRESH_SESSION_COORDINATION_ID,
    authStoreUser: () => currentUser,
    fetchUserInfo: vi.fn(async () => null),
    isRefreshStillCurrent: () => true,
    logout: vi.fn(),
    adoptRefreshedToken: vi.fn(),
    scheduleTransientRefreshRetry: vi.fn(),
    endLocalSession: vi.fn(),
    crossTabState: state(),
    postRefreshMessage: vi.fn(),
    ...overrides,
  }
}

beforeEach(() => {
  sessionStorage.clear()
  localStorage.clear()
  document.cookie = 'csrf_token=refresh-csrf; Path=/'
  grantLock()
})

afterEach(() => {
  document.cookie = 'csrf_token=; Max-Age=0; Path=/'
  vi.useRealTimers()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('cross-tab wait state', () => {
  it('clears an active waiter and resolves it with the requested result', async () => {
    vi.useFakeTimers()
    const currentState = state()
    const pending = waitForCrossTabRefresh(currentState, 'session')

    clearCrossTabWaiter(currentState, true)

    await expect(pending).resolves.toBe(true)
    expect(currentState.waiter).toBeNull()
  })

  it('resolves false and clears stale state after the wait deadline', async () => {
    vi.useFakeTimers()
    const currentState = state()
    currentState.inFlight = Promise.resolve(true)
    const pending = waitForCrossTabRefresh(currentState, 'session')

    await vi.advanceTimersByTimeAsync(CROSS_TAB_WAIT_TIMEOUT_MS)

    await expect(pending).resolves.toBe(false)
    expect(currentState.waiter).toBeNull()
    expect(currentState.inFlight).toBeNull()
  })
})

describe('runRefreshOperation', () => {
  it('refreshes through the server-held cookie and never sends a provider credential', async () => {
    const fetchMock = vi.fn().mockResolvedValue(response({
      access_token: 'next-access',
      refresh_session: true,
      expires_in: 3600,
    }))
    vi.stubGlobal('fetch', fetchMock)
    const adoptRefreshedToken = vi.fn()
    const postRefreshMessage = vi.fn()

    const ok = await runRefreshOperation(options({ adoptRefreshedToken, postRefreshMessage }))

    expect(ok).toBe(true)
    expect(fetchMock).toHaveBeenCalledOnce()
    const [, request] = fetchMock.mock.calls[0]
    expect(request).toEqual(expect.objectContaining({
      method: 'POST',
      headers: expect.objectContaining({
        'Content-Type': 'application/json',
        'X-CSRF-Token': 'refresh-csrf',
      }),
      body: JSON.stringify({ grant_type: 'refresh_token' }),
    }))
    expect(String(request.body)).not.toContain('refresh_token":"server-held')
    expect(adoptRefreshedToken).toHaveBeenCalledWith(
      expect.objectContaining({
        accessToken: 'next-access',
        refreshToken: REFRESH_SESSION_COORDINATION_ID,
      }),
      currentUser,
    )
    expect(postRefreshMessage).toHaveBeenCalledWith({
      type: 'refresh-started',
      sessionId: REFRESH_SESSION_COORDINATION_ID,
    })
    expect(postRefreshMessage).toHaveBeenLastCalledWith(expect.objectContaining({
      type: 'refresh-complete',
      ok: true,
      sessionId: REFRESH_SESSION_COORDINATION_ID,
    }))
    expect(localStorage.length).toBe(0)
    expect(sessionStorage.length).toBe(0)
  })

  it('derives the user from userinfo when no current identity is available', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({
      access_token: 'opaque-access',
      refresh_session: true,
    })))
    const fetchUserInfo = vi.fn(async () => ({ sub: 'userinfo-user' }))
    const adoptRefreshedToken = vi.fn()

    await expect(runRefreshOperation(options({
      authStoreUser: () => null,
      fetchUserInfo,
      adoptRefreshedToken,
    }))).resolves.toBe(true)

    expect(fetchUserInfo).toHaveBeenCalledWith('opaque-access')
    expect(adoptRefreshedToken).toHaveBeenCalledWith(
      expect.objectContaining({ accessToken: 'opaque-access' }),
      { sub: 'userinfo-user' },
    )
  })

  it('does not call the backend after the session was replaced before lock acquisition', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const endLocalSession = vi.fn()

    const ok = await runRefreshOperation(options({
      isRefreshStillCurrent: () => false,
      endLocalSession,
    }))

    expect(ok).toBe(false)
    expect(fetchMock).not.toHaveBeenCalled()
    expect(endLocalSession).not.toHaveBeenCalled()
  })

  it.each([
    [{ access_token: '' }, 'malformed token'],
    [{ access_token: 'next-access', refresh_session: false }, 'missing server session'],
    [{ access_token: 'next-access' }, 'missing refresh_session marker'],
  ])('fails closed for %s (%s)', async (body) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(body)))
    const endLocalSession = vi.fn()

    await expect(runRefreshOperation(options({ endLocalSession }))).resolves.toBe(false)

    expect(endLocalSession).toHaveBeenCalledOnce()
  })

  it.each(['invalid_grant', 'missing_refresh_cookie'])('logs out on %s', async (error) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ detail: { error } }, 401)))
    const logout = vi.fn()
    const endLocalSession = vi.fn()

    await expect(runRefreshOperation(options({ logout, endLocalSession }))).resolves.toBe(false)

    expect(logout).toHaveBeenCalledOnce()
    expect(endLocalSession).not.toHaveBeenCalled()
  })

  it('keeps the current session and schedules a retry on rate limiting', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ detail: 'slow down' }, 429)))
    const scheduleTransientRefreshRetry = vi.fn()
    const endLocalSession = vi.fn()

    await expect(runRefreshOperation(options({
      scheduleTransientRefreshRetry,
      endLocalSession,
    }))).resolves.toBe(false)

    expect(scheduleTransientRefreshRetry).toHaveBeenCalledOnce()
    expect(endLocalSession).not.toHaveBeenCalled()
  })

  it('fails closed for an ambiguous upstream failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ detail: 'provider failure' }, 502)))
    const endLocalSession = vi.fn()

    await expect(runRefreshOperation(options({ endLocalSession }))).resolves.toBe(false)

    expect(endLocalSession).toHaveBeenCalledOnce()
  })

  it('fails closed for network errors and still broadcasts completion', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')))
    vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const endLocalSession = vi.fn()
    const postRefreshMessage = vi.fn()

    await expect(runRefreshOperation(options({ endLocalSession, postRefreshMessage })))
      .resolves.toBe(false)

    expect(endLocalSession).toHaveBeenCalledOnce()
    expect(postRefreshMessage).toHaveBeenLastCalledWith(expect.objectContaining({
      type: 'refresh-complete',
      ok: false,
    }))
  })

  it('logs out when refresh succeeds but no identity can be established', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({
      access_token: 'opaque-access',
      refresh_session: true,
    })))
    const logout = vi.fn()

    await expect(runRefreshOperation(options({
      authStoreUser: () => null,
      fetchUserInfo: vi.fn(async () => null),
      logout,
    }))).resolves.toBe(false)

    expect(logout).toHaveBeenCalledOnce()
  })

  it('waits for the other tab when the Web Lock is unavailable', async () => {
    vi.useFakeTimers()
    denyLock()
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const currentState = state()
    const pending = runRefreshOperation(options({ crossTabState: currentState }))

    await vi.advanceTimersByTimeAsync(CROSS_TAB_WAIT_TIMEOUT_MS)

    await expect(pending).resolves.toBe(false)
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
