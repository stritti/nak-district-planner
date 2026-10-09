import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * Versions shown in the footer. Needs no sign-in on purpose: it also shows on
 * the login page, which is where a mismatched deployment is easiest to spot.
 */
export const useBuildInfoStore = defineStore('buildInfo', () => {
  const frontendVersion = __APP_VERSION__
  const backendVersion = ref<string | null>(null)

  async function load(): Promise<void> {
    try {
      // Plain fetch, not apiFetch: /api/health is public, and apiFetch would
      // react to a failure with a token refresh or even a logout.
      const response = await fetch('/api/health', { headers: { Accept: 'application/json' } })
      // A degraded backend answers 503 but still reports its version.
      const body: unknown = await response.json()
      const version = (body as { version?: unknown } | null)?.version
      backendVersion.value = typeof version === 'string' && version.length > 0 ? version : null
    } catch {
      backendVersion.value = null
    }
  }

  return { frontendVersion, backendVersion, load }
})
