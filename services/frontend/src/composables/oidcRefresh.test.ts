import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  clearCrossTabWaiter,
  clearRotationReceipts,
  CROSS_TAB_WAIT_TIMEOUT_MS,
  MAX_PERSISTED_RECEIPTS,
  parseStoredReceipt,
  prunePersistedReceipts,
  pruneRotatedTokens,
  RECEIPT_KEY_PREFIX,
  RECEIPT_STATE_CONSUMED,
  ROTATED_TOKEN_TTL_MS,
  rotationReceiptKey,
  runRefreshOperation,
  waitForCrossTabRefresh,
  type CrossTabRefreshState,
  type RotationReceipt,
} from './oidcRefresh'
import type { OIDCToken } from './useOIDC'

const validToken: OIDCToken = {
  accessToken: 'access',
  idToken: 'id',
  refreshToken: 'refresh',
  expiresAt: 1_800_000_000,
}

function receipt(overrides: Partial<RotationReceipt> = {}): RotationReceipt {
  return {
    token: validToken,
    user: { sub: 'user' },
    recordedAt: Date.now(),
    ...overrides,
  }
}

function state(): CrossTabRefreshState {
  return { inFlight: Promise.resolve(true), waiter: null }
}

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('parseStoredReceipt', () => {
  it('distinguishes absent, pending, and consumed markers', () => {
    expect(parseStoredReceipt(null)).toEqual({ state: 'absent' })
    expect(parseStoredReceipt('')).toEqual({ state: 'pending' })
    expect(parseStoredReceipt(RECEIPT_STATE_CONSUMED)).toEqual({ state: 'consumed' })
  })

  it('accepts a complete rotation receipt', () => {
    const value = receipt()
    expect(parseStoredReceipt(JSON.stringify(value))).toEqual({ state: 'rotation', receipt: value })
  })

  it.each([
    '{broken',
    'null',
    JSON.stringify({ token: validToken, user: { sub: '' }, recordedAt: Date.now() }),
    JSON.stringify({ token: validToken, user: null }),
    JSON.stringify({ token: { ...validToken, refreshToken: '' }, user: { sub: 'user' }, recordedAt: Date.now() }),
    JSON.stringify({ token: validToken, user: { sub: 'user' }, recordedAt: Number.NaN }),
  ])('fails closed for invalid data %s', (raw) => {
    expect(parseStoredReceipt(raw)).toEqual({ state: 'invalid' })
  })
})

describe('rotation receipts in localStorage', () => {
  it('hashes the refresh token before using it in the storage key', async () => {
    const key = await rotationReceiptKey('secret-refresh-value')

    expect(key).toMatch(/^oidc-refresh-result:[A-Za-z0-9_-]+$/)
    expect(key).not.toContain('secret-refresh-value')
    expect(await rotationReceiptKey('secret-refresh-value')).toBe(key)
  })

  it('scrubs completed receipts into tombstones and retains replay-protection markers', () => {
    localStorage.setItem(`${RECEIPT_KEY_PREFIX}pending`, '')
    localStorage.setItem(`${RECEIPT_KEY_PREFIX}consumed`, RECEIPT_STATE_CONSUMED)
    localStorage.setItem(`${RECEIPT_KEY_PREFIX}complete`, JSON.stringify(receipt()))
    localStorage.setItem('unrelated', 'preserve')

    clearRotationReceipts()

    expect(localStorage.getItem(`${RECEIPT_KEY_PREFIX}pending`)).toBe('')
    expect(localStorage.getItem(`${RECEIPT_KEY_PREFIX}consumed`)).toBe(RECEIPT_STATE_CONSUMED)
    expect(localStorage.getItem(`${RECEIPT_KEY_PREFIX}complete`)).toBe(RECEIPT_STATE_CONSUMED)
    expect(localStorage.getItem('unrelated')).toBe('preserve')
  })

  it('expires invalid or stale receipts and bounds retained completed receipts', () => {
    vi.useFakeTimers()
    const now = new Date('2026-09-26T12:00:00Z')
    vi.setSystemTime(now)
    localStorage.setItem(`${RECEIPT_KEY_PREFIX}pending`, '')
    localStorage.setItem(`${RECEIPT_KEY_PREFIX}expired`, JSON.stringify(receipt({ recordedAt: now.getTime() - 25 * 60 * 60 * 1000 })))
    localStorage.setItem(`${RECEIPT_KEY_PREFIX}future`, JSON.stringify(receipt({ recordedAt: now.getTime() + 1 })))
    localStorage.setItem(`${RECEIPT_KEY_PREFIX}malformed`, '{broken')
    for (let index = 0; index <= MAX_PERSISTED_RECEIPTS; index += 1) {
      localStorage.setItem(
        `${RECEIPT_KEY_PREFIX}receipt-${index}`,
        JSON.stringify(receipt({ recordedAt: now.getTime() - index })),
      )
    }

    prunePersistedReceipts()

    expect(localStorage.getItem(`${RECEIPT_KEY_PREFIX}pending`)).toBe('')
    expect(localStorage.getItem(`${RECEIPT_KEY_PREFIX}expired`)).toBe(RECEIPT_STATE_CONSUMED)
    expect(localStorage.getItem(`${RECEIPT_KEY_PREFIX}future`)).toBe(RECEIPT_STATE_CONSUMED)
    expect(localStorage.getItem(`${RECEIPT_KEY_PREFIX}malformed`)).toBe('{broken')
    expect(localStorage.getItem(`${RECEIPT_KEY_PREFIX}receipt-0`)).not.toBe(RECEIPT_STATE_CONSUMED)
    expect(localStorage.getItem(`${RECEIPT_KEY_PREFIX}receipt-${MAX_PERSISTED_RECEIPTS}`))
      .toBe(RECEIPT_STATE_CONSUMED)
  })
})

describe('cross-tab wait state', () => {
  it('clears an active waiter and resolves it with the requested result', async () => {
    vi.useFakeTimers()
    const currentState = state()
    const pending = waitForCrossTabRefresh(currentState, 'refresh')

    clearCrossTabWaiter(currentState, true)

    await expect(pending).resolves.toBe(true)
    expect(currentState.waiter).toBeNull()
  })

  it('resolves false and clears stale state after the wait deadline', async () => {
    vi.useFakeTimers()
    const currentState = state()
    const pending = waitForCrossTabRefresh(currentState, 'refresh')

    await vi.advanceTimersByTimeAsync(CROSS_TAB_WAIT_TIMEOUT_MS)

    await expect(pending).resolves.toBe(false)
    expect(currentState.waiter).toBeNull()
    expect(currentState.inFlight).toBeNull()
  })

  it('prunes expired in-memory rotations without removing current ones', () => {
    vi.useFakeTimers()
    const now = new Date('2026-09-26T12:00:00Z')
    vi.setSystemTime(now)
    const rotations = new Map<string, RotationReceipt>([
      ['fresh', receipt({ recordedAt: now.getTime() })],
      ['expired', receipt({ recordedAt: now.getTime() - ROTATED_TOKEN_TTL_MS - 1 })],
    ])

    pruneRotatedTokens(rotations)

    expect([...rotations.keys()]).toEqual(['fresh'])
  })

  it('removes a pending marker when the session becomes stale before the fetch', async () => {
    const fetchSpy = vi.fn()
    const endLocalSession = vi.fn()
    const currentState: CrossTabRefreshState = { inFlight: null, waiter: null }
    vi.stubGlobal('fetch', fetchSpy)
    vi.stubGlobal('navigator', {
      locks: {
        request: async (_name: string, _options: unknown, callback: (lock: object) => Promise<boolean>) =>
          callback({ name: 'refresh-lock' }),
      },
    })

    const ok = await runRefreshOperation({
      currentToken: validToken,
      refreshTokenUsed: 'refresh',
      authStoreToken: () => validToken,
      authStoreUser: () => ({ sub: 'user' }),
      fetchUserInfo: async () => null,
      isRefreshStillCurrent: () => false,
      logout: vi.fn(),
      adoptRotatedToken: vi.fn(),
      onExpiredSuccessor: vi.fn(),
      scheduleTransientRefreshRetry: vi.fn(),
      endLocalSession,
      rotatedTokens: new Map(),
      crossTabState: currentState,
      postRefreshMessage: vi.fn(),
    })

    const key = await rotationReceiptKey('refresh')
    expect(ok).toBe(false)
    expect(fetchSpy).not.toHaveBeenCalled()
    expect(localStorage.getItem(key)).toBeNull()
    expect(endLocalSession).not.toHaveBeenCalled()
  })

  it('fails closed when the token endpoint returns an invalid access token shape', async () => {
    const endLocalSession = vi.fn()
    const postRefreshMessage = vi.fn()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ access_token: { unexpected: true } }), { status: 200 }),
    ))
    vi.stubGlobal('navigator', {
      locks: {
        request: async (_name: string, _options: unknown, callback: (lock: object) => Promise<boolean>) =>
          callback({ name: 'refresh-lock' }),
      },
    })

    const ok = await runRefreshOperation({
      currentToken: validToken,
      refreshTokenUsed: 'refresh',
      authStoreToken: () => validToken,
      authStoreUser: () => ({ sub: 'user' }),
      fetchUserInfo: async () => null,
      isRefreshStillCurrent: () => true,
      logout: vi.fn(),
      adoptRotatedToken: vi.fn(),
      onExpiredSuccessor: vi.fn(),
      scheduleTransientRefreshRetry: vi.fn(),
      endLocalSession,
      rotatedTokens: new Map(),
      crossTabState: { inFlight: null, waiter: null },
      postRefreshMessage,
    })

    expect(ok).toBe(false)
    expect(endLocalSession).toHaveBeenCalledOnce()
    expect(localStorage.getItem(await rotationReceiptKey('refresh'))).toBe('')
    expect(postRefreshMessage).toHaveBeenCalledWith(expect.objectContaining({
      type: 'refresh-complete',
      ok: false,
    }))
  })
})
