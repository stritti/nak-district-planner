/**
 * Pinia Auth Store
 *
 * Authentication tokens are intentionally kept in memory only. The provider
 * refresh token is held by the backend in an HttpOnly cookie and must never be
 * persisted in JavaScript-accessible browser storage.
 */

import { clearSessionViewSettings, setSessionSettingsIdentity } from '../composables/useSessionViewSettings'
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { OIDCToken, OIDCUser } from '../composables/oidcTypes'
import { getAccessContext, getCurrentUser, type MembershipAccess } from '../api/auth'
import { getPendingRegistrationsOverview } from '../api/registrations'

export const useAuthStore = defineStore(
  'auth',
  () => {
    const token = ref<OIDCToken | null>(null)
    const user = ref<OIDCUser | null>(null)
    const isSuperadmin = ref(false)
    const accessStatus = ref<'ACTIVE' | 'PENDING_APPROVAL'>('PENDING_APPROVAL')
    const memberships = ref<MembershipAccess[]>([])
    const pendingRegistrationsCount = ref(0)

    const isAuthenticated = computed(() => token.value !== null)
    const isTokenExpired = computed(() => {
      if (!token.value) return true
      return Date.now() / 1000 >= token.value.expiresAt
    })

    function setToken(newToken: OIDCToken | null, newUser: OIDCUser | null = null) {
      if (user.value && user.value.sub !== newUser?.sub) clearSessionViewSettings()
      setSessionSettingsIdentity(newUser?.sub ?? null)
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
      return token.value.accessToken || token.value.idToken
    }

    function clearAuth() {
      clearSessionViewSettings()
      token.value = null
      user.value = null
      isSuperadmin.value = false
      accessStatus.value = 'PENDING_APPROVAL'
      memberships.value = []
      pendingRegistrationsCount.value = 0
    }

    return {
      token,
      user,
      isSuperadmin,
      accessStatus,
      memberships,
      pendingRegistrationsCount,
      isAuthenticated,
      isTokenExpired,
      setToken,
      refreshCurrentUserFlags,
      getToken,
      clearAuth,
    }
  },
)
