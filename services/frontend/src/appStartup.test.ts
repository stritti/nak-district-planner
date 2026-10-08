import { describe, expect, it, vi } from 'vitest'
import {
  refreshAuthenticatedUserOnStartup,
  registerServiceWorkerOnLoad,
  type StartupAuthStore,
} from './appStartup'

function authStore(overrides: Partial<StartupAuthStore> = {}): StartupAuthStore {
  return {
    isAuthenticated: false,
    refreshCurrentUserFlags: vi.fn().mockResolvedValue(undefined),
    clearAuth: vi.fn(),
    ...overrides,
  }
}

describe('app startup', () => {
  it('does not refresh flags for unauthenticated users', () => {
    const store = authStore()

    refreshAuthenticatedUserOnStartup(store)

    expect(store.refreshCurrentUserFlags).not.toHaveBeenCalled()
    expect(store.clearAuth).not.toHaveBeenCalled()
  })

  it('refreshes flags for authenticated users', async () => {
    const refresh = vi.fn().mockResolvedValue(undefined)
    const store = authStore({ isAuthenticated: true, refreshCurrentUserFlags: refresh })

    refreshAuthenticatedUserOnStartup(store)
    await refresh.mock.results[0].value

    expect(refresh).toHaveBeenCalledOnce()
    expect(store.clearAuth).not.toHaveBeenCalled()
  })

  it('clears authentication when the startup refresh fails', async () => {
    const error = new Error('unauthorized')
    const refresh = vi.fn().mockRejectedValue(error)
    const clearAuth = vi.fn()
    const store = authStore({
      isAuthenticated: true,
      refreshCurrentUserFlags: refresh,
      clearAuth,
    })

    refreshAuthenticatedUserOnStartup(store)
    await refresh.mock.results[0].value.catch(() => undefined)
    await Promise.resolve()

    expect(clearAuth).toHaveBeenCalledOnce()
  })

  it('does not register a load handler without service worker support', () => {
    const addEventListener = vi.fn()

    registerServiceWorkerOnLoad(
      { serviceWorker: undefined } as unknown as Navigator,
      { addEventListener } as unknown as Window,
    )

    expect(addEventListener).not.toHaveBeenCalled()
  })

  it('registers the service worker on load and tolerates registration failure', async () => {
    const register = vi.fn().mockRejectedValue(new Error('registration failed'))
    let loadHandler: (() => void) | undefined
    const addEventListener = vi.fn((event: string, handler: EventListenerOrEventListenerObject) => {
      if (event === 'load' && typeof handler === 'function') loadHandler = handler as () => void
    })

    registerServiceWorkerOnLoad(
      { serviceWorker: { register } } as unknown as Navigator,
      { addEventListener } as unknown as Window,
    )

    expect(addEventListener).toHaveBeenCalledWith('load', expect.any(Function))
    expect(loadHandler).toBeDefined()
    loadHandler?.()
    await Promise.resolve()

    expect(register).toHaveBeenCalledWith('/sw.js')
  })
})
