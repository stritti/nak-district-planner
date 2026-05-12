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
import type { OIDCToken, OIDCUser } from '../composables/useOIDC'
import { getAccessContext, getCurrentUser, type MembershipAccess } from '../api/auth'
import { getPendingRegistrationsOverview } from '../api/registrations'

export const useAuthStore = defineStore(
  'auth',
  () => {
    // State
    const token = ref<OIDCToken | null>(null)
    const user = ref<OIDCUser | null>(null)
    const isSuperadmin = ref(false)
    const accessStatus = ref<'ACTIVE' | 'PENDING_APPROVAL'>('PENDING_APPROVAL')
    const memberships = ref<MembershipAccess[]>([])
    const pendingRegistrationsCount = ref(0)

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

    async function refreshCurrentUserFlags() {
      if (!isAuthenticated.value) {
        isSuperadmin.value = false
        return
      }
      try {
        const me = await getCurrentUser()
        isSuperadmin.value = me.is_superadmin
        const access = await getAccessContext()
        accessStatus.value = access.status
        memberships.value = access.memberships

        // Show prominent pending-registration hint for superadmins and district admins.
        const canSeePendingRegistrations =
          isSuperadmin.value ||
          access.memberships.some((m) => m.role === 'DISTRICT_ADMIN')

        if (canSeePendingRegistrations) {
          const overview = await getPendingRegistrationsOverview()
          pendingRegistrationsCount.value = overview.total_pending
        } else {
          pendingRegistrationsCount.value = 0
        }
      } catch (error) {
        // Non-blocking: auth/session stays valid even if profile flags endpoint fails.
        isSuperadmin.value = false
        accessStatus.value = 'PENDING_APPROVAL'
        memberships.value = []
        pendingRegistrationsCount.value = 0
        console.warn('Unable to refresh current user flags', error)
      }
    }

    function getToken(): string | null {
      if (!token.value) return null
      if (isTokenExpired.value) return null
      // Backend API expects OAuth access token as Bearer token.
      return token.value.accessToken || token.value.idToken
    }

    function clearAuth() {
      token.value = null
      user.value = null
      isSuperadmin.value = false
      accessStatus.value = 'PENDING_APPROVAL'
      memberships.value = []
      pendingRegistrationsCount.value = 0
    }

    return {
      // State - return refs directly for proper reactivity
      token,
      user,
      isSuperadmin,
      accessStatus,
      memberships,
      pendingRegistrationsCount,
      isAuthenticated,
      isTokenExpired,

      // Actions
      setToken,
      refreshCurrentUserFlags,
      getToken,
      clearAuth,
    }
  },
  {
    persist: true,
  }
)
