// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { ref } from 'vue'
import type { OIDCDiscovery } from './oidcTypes'

/**
 * Discovery client for the backend OIDC proxy. Kept as a module-level
 * singleton because the discovery document is app-wide immutable state;
 * every composable instance shares the same cached document and promise.
 */
const discovery = ref<OIDCDiscovery | null>(null)
const clientId = ref<string>('')
const discoveryPromise = ref<Promise<void> | null>(null)
const isLoading = ref(false)
const error = ref<string | null>(null)

export function useDiscoveryState() {
  return { discovery, clientId, isLoading, error }
}

/** @internal — resets module-level state; used by tests */
export function __resetDiscoveryState(): void {
  discovery.value = null
  clientId.value = ''
  discoveryPromise.value = null
  isLoading.value = false
  error.value = null
}

export async function loadDiscovery(): Promise<void> {
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
