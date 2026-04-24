/**
 * Tests for auth store
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from './auth'
import type { OIDCToken, OIDCUser } from '../composables/useOIDC'
import * as authApi from '../api/auth'
import * as registrationsApi from '../api/registrations'

describe('useAuthStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should initialize with no authentication', () => {
    const store = useAuthStore()

    expect(store.isAuthenticated).toBe(false)
    expect(store.token).toBeNull()
    expect(store.user).toBeNull()
  })

  it('should set token and user', () => {
    const store = useAuthStore()

    const mockToken: OIDCToken = {
      accessToken: 'test_token',
      idToken: 'test_id_token',
      refreshToken: 'test_refresh_token',
      expiresAt: Math.floor(Date.now() / 1000) + 3600,
    }

    const mockUser: OIDCUser = {
      sub: 'user-123',
      email: 'test@example.com',
      name: 'Test User',
    }

    store.setToken(mockToken, mockUser)

    expect(store.isAuthenticated).toBe(true)
    expect(store.token).toEqual(mockToken)
    expect(store.user).toEqual(mockUser)
  })

  it('should return token if not expired', () => {
    const store = useAuthStore()

    const mockToken: OIDCToken = {
      accessToken: 'test_token',
      idToken: 'test_id_token',
      expiresAt: Math.floor(Date.now() / 1000) + 3600, // 1 hour from now
    }

    store.setToken(mockToken)

    expect(store.getToken()).toBe('test_token')
  })

  it('should return null if token expired', () => {
    const store = useAuthStore()

    const mockToken: OIDCToken = {
      accessToken: 'test_token',
      idToken: 'test_id_token',
      expiresAt: Math.floor(Date.now() / 1000) - 3600, // 1 hour ago
    }

    store.setToken(mockToken)

    expect(store.getToken()).toBeNull()
  })

  it('should clear authentication', () => {
    const store = useAuthStore()

    const mockToken: OIDCToken = {
      accessToken: 'test_token',
      idToken: 'test_id_token',
      expiresAt: Math.floor(Date.now() / 1000) + 3600,
    }

    store.setToken(mockToken)
    expect(store.isAuthenticated).toBe(true)

    store.clearAuth()

    expect(store.isAuthenticated).toBe(false)
    expect(store.token).toBeNull()
    expect(store.user).toBeNull()
  })

  it('should detect expired token', () => {
    const store = useAuthStore()

    const mockToken: OIDCToken = {
      accessToken: 'test_token',
      idToken: 'test_id_token',
      expiresAt: Math.floor(Date.now() / 1000) - 1, // Already expired
    }

    store.setToken(mockToken)

    expect(store.isTokenExpired).toBe(true)
  })

  it('should not throw when refreshCurrentUserFlags fails', async () => {
    const store = useAuthStore()
    const mockToken: OIDCToken = {
      accessToken: 'test_token',
      idToken: 'test_id_token',
      expiresAt: Math.floor(Date.now() / 1000) + 3600,
    }
    store.setToken(mockToken)

    const spyUser = vi.spyOn(authApi, 'getCurrentUser').mockRejectedValueOnce(new Error('401'))
    const spyAccess = vi.spyOn(authApi, 'getAccessContext').mockResolvedValueOnce({
      status: 'PENDING_APPROVAL',
      memberships: [],
    })
    const spyPending = vi
      .spyOn(registrationsApi, 'getPendingRegistrationsOverview')
      .mockResolvedValueOnce({ total_pending: 0, by_district: [] })

    await expect(store.refreshCurrentUserFlags()).resolves.toBeUndefined()
    expect(store.isSuperadmin).toBe(false)
    spyUser.mockRestore()
    spyAccess.mockRestore()
    spyPending.mockRestore()
  })

  it('should update access context on successful refresh', async () => {
    const store = useAuthStore()
    const mockToken: OIDCToken = {
      accessToken: 'test_token',
      idToken: 'test_id_token',
      expiresAt: Math.floor(Date.now() / 1000) + 3600,
    }
    store.setToken(mockToken)

    const spyUser = vi.spyOn(authApi, 'getCurrentUser').mockResolvedValueOnce({
      sub: 'u1',
      email: 'u1@example.com',
      username: 'u1',
      name: null,
      given_name: null,
      family_name: null,
      is_superadmin: false,
    })
    const spyAccess = vi.spyOn(authApi, 'getAccessContext').mockResolvedValueOnce({
      status: 'PENDING_APPROVAL',
      memberships: [],
    })
    const spyPending = vi
      .spyOn(registrationsApi, 'getPendingRegistrationsOverview')
      .mockResolvedValueOnce({ total_pending: 0, by_district: [] })

    await store.refreshCurrentUserFlags()

    expect(store.isSuperadmin).toBe(false)
    expect(store.accessStatus).toBe('PENDING_APPROVAL')
    expect(store.memberships).toEqual([])
    expect(store.pendingRegistrationsCount).toBe(0)
    spyUser.mockRestore()
    spyAccess.mockRestore()
    spyPending.mockRestore()
  })

  it('should load pending registrations for superadmin', async () => {
    const store = useAuthStore()
    const mockToken: OIDCToken = {
      accessToken: 'test_token',
      idToken: 'test_id_token',
      expiresAt: Math.floor(Date.now() / 1000) + 3600,
    }
    store.setToken(mockToken)

    const spyUser = vi.spyOn(authApi, 'getCurrentUser').mockResolvedValueOnce({
      sub: 'admin',
      email: 'admin@example.com',
      username: 'admin',
      name: null,
      given_name: null,
      family_name: null,
      is_superadmin: true,
    })
    const spyAccess = vi.spyOn(authApi, 'getAccessContext').mockResolvedValueOnce({
      status: 'ACTIVE',
      memberships: [],
    })
    const spyPending = vi
      .spyOn(registrationsApi, 'getPendingRegistrationsOverview')
      .mockResolvedValueOnce({
        total_pending: 3,
        by_district: [{ district_id: 'd1', pending: 3 }],
      })

    await store.refreshCurrentUserFlags()

    expect(store.pendingRegistrationsCount).toBe(3)
    spyUser.mockRestore()
    spyAccess.mockRestore()
    spyPending.mockRestore()
  })
})
