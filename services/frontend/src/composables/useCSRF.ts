// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

/**
 * CSRF token helpers for the frontend double-submit flow.
 */

import { onMounted, ref } from 'vue'

export interface CSRFConfig {
  cookieName?: string
  headerName?: string
}

const DEFAULT_COOKIE_NAME = 'csrf_token'
const DEFAULT_HEADER_NAME = 'X-CSRF-Token'

/** Read a cookie value without introducing another browser dependency. */
export function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop()?.split(';').shift() || null
  return null
}

/**
 * Read the current CSRF cookie at request time.
 *
 * OIDC token/refresh/revoke calls bypass apiFetch and therefore use this
 * helper directly. Reading lazily also picks up middleware token rotation.
 */
export function getCurrentCSRFHeaders(config: CSRFConfig = {}): Record<string, string> {
  const cookieName = config.cookieName ?? DEFAULT_COOKIE_NAME
  const headerName = config.headerName ?? DEFAULT_HEADER_NAME
  const token = getCookie(cookieName)
  return token ? { [headerName]: token } : {}
}

export function useCSRF(config: CSRFConfig = {}) {
  const cookieName = config.cookieName ?? DEFAULT_COOKIE_NAME
  const headerName = config.headerName ?? DEFAULT_HEADER_NAME
  const csrfToken = ref<string>('')

  const loadCSRFToken = () => {
    csrfToken.value = getCookie(cookieName) || ''
  }

  const getCSRFHeaders = () => {
    // Prefer the current cookie so request headers follow server-side token
    // rotation instead of a potentially stale value captured on mount.
    const current = getCurrentCSRFHeaders({ cookieName, headerName })
    if (current[headerName]) csrfToken.value = current[headerName]
    return current
  }

  const hasCSRFToken = () => Boolean(getCookie(cookieName) || csrfToken.value)
  const getToken = () => getCookie(cookieName) || csrfToken.value

  onMounted(loadCSRFToken)

  return {
    csrfToken,
    loadCSRFToken,
    getCSRFHeaders,
    hasCSRFToken,
    getToken,
  }
}
