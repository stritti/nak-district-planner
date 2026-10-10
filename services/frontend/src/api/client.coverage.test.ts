// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiFetch } from './client'
import { ApiError, UnauthorizedError } from './errors'

const mocks = vi.hoisted(() => ({
  authStore: {
    token: null as null | { accessToken: string },
    isTokenExpired: false,
    getToken: vi.fn(),
    clearAuth: vi.fn(),
  },
  oidc: {
    getSessionGeneration: vi.fn(),
    refreshToken: vi.fn(),
  },
  routerPush: vi.fn(),
}))

vi.mock('../stores/auth', () => ({ useAuthStore: () => mocks.authStore }))
vi.mock('../composables/useOIDC', () => ({ useOIDC: () => mocks.oidc }))
vi.mock('../composables/useCSRF', () => ({
  useCSRF: () => ({ getCSRFHeaders: () => ({ 'X-CSRF-Token': 'csrf' }) }),
}))
vi.mock('../router', () => ({ router: { push: mocks.routerPush } }))

function response(body: unknown, status = 200): Response {
  return new Response(
    body === undefined ? null : typeof body === 'string' ? body : JSON.stringify(body),
    { status, headers: { 'content-type': 'application/json' } },
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  mocks.authStore.token = null
  mocks.authStore.isTokenExpired = false
  mocks.authStore.getToken.mockImplementation(() => mocks.authStore.token?.accessToken ?? null)
  mocks.oidc.getSessionGeneration.mockReturnValue(1)
  mocks.oidc.refreshToken.mockResolvedValue(true)
  vi.stubGlobal('fetch', vi.fn())
})

describe('apiFetch coverage gaps', () => {
  it('refreshes an already expired access token before the request', async () => {
    mocks.authStore.token = { accessToken: 'expired' }
    mocks.authStore.isTokenExpired = true
    mocks.oidc.refreshToken.mockImplementation(async () => {
      mocks.authStore.token = { accessToken: 'fresh' }
      return true
    })
    vi.mocked(fetch).mockResolvedValue(response({ ok: true }))

    await expect(apiFetch('/api/v1/test')).resolves.toEqual({ ok: true })
    expect(mocks.oidc.refreshToken).toHaveBeenCalledTimes(1)
    expect((vi.mocked(fetch).mock.calls[0][1]?.headers as Record<string, string>).Authorization)
      .toBe('Bearer fresh')
  })

  it('fails closed when a preflight refresh is discarded or changes session', async () => {
    mocks.authStore.token = { accessToken: 'expired' }
    mocks.authStore.isTokenExpired = true
    mocks.oidc.refreshToken.mockResolvedValueOnce(false)
    await expect(apiFetch('/api/v1/test')).rejects.toBeInstanceOf(UnauthorizedError)

    mocks.oidc.refreshToken.mockResolvedValueOnce(true)
    mocks.oidc.getSessionGeneration.mockReturnValueOnce(1).mockReturnValueOnce(2)
    await expect(apiFetch('/api/v1/test')).rejects.toBeInstanceOf(UnauthorizedError)
    expect(fetch).not.toHaveBeenCalled()
  })

  it('does not refresh the auth/me endpoint on 401', async () => {
    vi.mocked(fetch).mockResolvedValue(response('Unauthorized', 401))

    const error = await apiFetch('/api/v1/auth/me').catch((value: unknown) => value)

    expect(error).toBeInstanceOf(ApiError)
    expect(mocks.oidc.refreshToken).not.toHaveBeenCalled()
  })

  it('refreshes once after a 401 and retries with the new bearer', async () => {
    mocks.authStore.token = { accessToken: 'old' }
    mocks.oidc.refreshToken.mockImplementation(async () => {
      mocks.authStore.token = { accessToken: 'new' }
      return true
    })
    vi.mocked(fetch)
      .mockResolvedValueOnce(response('Unauthorized', 401))
      .mockResolvedValueOnce(response({ retried: true }))

    await expect(apiFetch('/api/v1/test')).resolves.toEqual({ retried: true })
    expect(fetch).toHaveBeenCalledTimes(2)
    expect((vi.mocked(fetch).mock.calls[1][1]?.headers as Record<string, string>).Authorization)
      .toBe('Bearer new')
  })

  it('fails closed when the 401 refresh is discarded', async () => {
    mocks.authStore.token = { accessToken: 'old' }
    mocks.oidc.refreshToken.mockResolvedValue(false)
    vi.mocked(fetch).mockResolvedValue(response('Unauthorized', 401))

    await expect(apiFetch('/api/v1/test')).rejects.toBeInstanceOf(UnauthorizedError)
  })

  it('clears auth when refresh succeeds without producing a token', async () => {
    mocks.authStore.token = { accessToken: 'old' }
    mocks.oidc.refreshToken.mockImplementation(async () => {
      mocks.authStore.token = null
      return true
    })
    vi.mocked(fetch).mockResolvedValue(response('Unauthorized', 401))

    await expect(apiFetch('/api/v1/test')).rejects.toBeInstanceOf(UnauthorizedError)
    expect(mocks.authStore.clearAuth).toHaveBeenCalledTimes(1)
    expect(mocks.routerPush).toHaveBeenCalledWith('/login')
  })

  it('reloads on CSRF validation failures', async () => {
    const reload = vi.spyOn(window.location, 'reload').mockImplementation(() => undefined)
    vi.mocked(fetch).mockResolvedValue(response('CSRF validation failed', 403))

    await expect(apiFetch('/api/v1/test')).rejects.toThrow('CSRF validation failed')
    expect(reload).toHaveBeenCalledTimes(1)
  })

  it('keeps plain text error bodies when JSON parsing fails', async () => {
    vi.mocked(fetch).mockResolvedValue(response('plain failure', 422))

    const error = await apiFetch('/api/v1/test').catch((value: unknown) => value)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).body).toBe('plain failure')
  })

  it('handles response text read failures', async () => {
    const res = response('ignored', 500)
    vi.spyOn(res, 'text').mockRejectedValue(new Error('body unavailable'))
    vi.mocked(fetch).mockResolvedValue(res)

    const error = await apiFetch('/api/v1/test').catch((value: unknown) => value)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).body).toBeUndefined()
  })
})
