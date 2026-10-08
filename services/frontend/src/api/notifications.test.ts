import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./client')

import * as client from './client'
import {
  dismissNotification,
  getUnreadCount,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from './notifications'

const apiFetch = vi.mocked(client.apiFetch)

describe('notification API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiFetch.mockResolvedValue({})
  })

  it('lists without a query string when no effective filters are supplied', async () => {
    await listNotifications('district-1')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/notifications/district-1')

    await listNotifications('district-1', { unreadOnly: false, limit: 0, offset: 0 })
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/notifications/district-1')
  })

  it('serializes every supported list filter', async () => {
    await listNotifications('district-1', { unreadOnly: true, limit: 25, offset: 50 })
    expect(apiFetch).toHaveBeenLastCalledWith(
      '/api/v1/notifications/district-1?unread_only=true&limit=25&offset=50',
    )
  })

  it('covers unread count and mutation endpoints', async () => {
    await getUnreadCount('district-1')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/notifications/district-1/unread-count')

    await markNotificationRead('notification-1')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/notifications/notification-1/read', {
      method: 'POST',
    })

    await dismissNotification('notification-1')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/notifications/notification-1/dismiss', {
      method: 'POST',
    })

    await markAllNotificationsRead('district-1')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/notifications/district-1/read-all', {
      method: 'POST',
    })
  })
})
