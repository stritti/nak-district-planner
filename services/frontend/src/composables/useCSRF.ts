/**
 * CSRF Token Management Composable for Vue 3
 * 
 * Provides CSRF token handling for protection against Cross-Site Request Forgery.
 * Uses the Double-Submit Pattern with cookies and custom headers.
 */

import { ref, onMounted } from 'vue'
import { useCookies } from '@vueuse/integrations/useCookies'

export interface CSRFConfig {
  cookieName?: string
  headerName?: string
}

export function useCSRF(config: CSRFConfig = {}) {
  const {
    cookieName = 'csrf_token',
    headerName = 'X-CSRF-Token',
  } = config

  const cookies = useCookies()
  const csrfToken = ref<string>('')

  /**
   * Load CSRF token from cookie
   */
  const loadCSRFToken = () => {
    csrfToken.value = cookies.get(cookieName) || ''
  }

  /**
   * Get CSRF headers for API requests
   */
  const getCSRFHeaders = () => {
    return {
      [headerName]: csrfToken.value,
    }
  }

  /**
   * Check if CSRF token is available
   */
  const hasCSRFToken = () => {
    return !!csrfToken.value
  }

  /**
   * Get the raw CSRF token value
   */
  const getToken = () => {
    return csrfToken.value
  }

  /**
   * Initialize CSRF token from cookie
   * Called automatically on component mount
   */
  onMounted(() => {
    loadCSRFToken()
  })

  return {
    csrfToken,
    loadCSRFToken,
    getCSRFHeaders,
    hasCSRFToken,
    getToken,
  }
}
