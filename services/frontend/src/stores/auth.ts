/**
 * Pinia Auth Store
 * 
 * Manages:
 * - User authentication state
 * - Token storage (persistent via localStorage)
 * - Auto-token-refresh logic
 * - getToken() for API calls
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { OIDCToken, OIDCUser } from '@/composables/useOIDC'

export const useAuthStore = defineStore(
  'auth',
  () => {
    // State
    const token = ref<OIDCToken | null>(null)
    const user = ref<OIDCUser | null>(null)

    // Computed
    const isAuthenticated = computed(() => token.value !== null)
    const isTokenExpired = computed(() => {
      if (!token.value) return true
      return Date.now() / 1000 >= token.value.expiresAt
    })

    // Actions
    function setToken(newToken: OIDCToken | null, newUser: OIDCUser | null = null) {
      token.value = newToken
      user.value = newUser
    }

    function getToken(): string | null {
      if (!token.value) return null
      if (isTokenExpired.value) return null
      return token.value.accessToken
    }

    function clearAuth() {
      token.value = null
      user.value = null
    }

    return {
      // State - return refs directly for proper reactivity
      token,
      user,
      isAuthenticated,
      isTokenExpired,

      // Actions
      setToken,
      getToken,
      clearAuth,
    }
  },
  {
    persist: true,
  }
)
