export interface StartupAuthStore {
  isAuthenticated: boolean
  refreshCurrentUserFlags: () => Promise<void>
  clearAuth: () => void
}

export function refreshAuthenticatedUserOnStartup(authStore: StartupAuthStore): void {
  if (!authStore.isAuthenticated) return

  void authStore.refreshCurrentUserFlags().catch(() => {
    authStore.clearAuth()
  })
}

export function registerServiceWorkerOnLoad(
  navigatorObject: Navigator,
  windowObject: Window,
): void {
  if (!navigatorObject.serviceWorker) return

  windowObject.addEventListener('load', () => {
    void navigatorObject.serviceWorker.register('/sw.js').catch(() => {
      // The application remains usable without offline caching.
    })
  })
}
