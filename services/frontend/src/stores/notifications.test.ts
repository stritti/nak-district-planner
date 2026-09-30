import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import * as api from '../api/notifications'
import { useNotificationStore } from './notifications'

vi.mock('../api/notifications')

const makeNotification = (
  id: string,
  readAt: string | null = null,
): api.NotificationItem => ({
  id,
  district_id: 'district-one',
  congregation_id: null,
  type: 'SYSTEM',
  title: 'Information',
  body: 'Test',
  payload: {},
  read_at: readAt,
  dismissed_at: null,
  created_at: '2026-09-30T08:00:00Z',
})

function loadedNotifications(...items: api.NotificationItem[]): api.NotificationListResponse {
  return { items, total: items.length, limit: 50, offset: 0 }
}

function prepareStore() {
  const pinia = createPinia()
  setActivePinia(pinia)
  return useNotificationStore()
}

describe('notification store', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.getUnreadCount).mockResolvedValue({ count: 0 })
  })

  it('dismisses unread notifications and adjusts the badge once', async () => {
    const store = prepareStore()
    vi.mocked(api.listNotifications).mockResolvedValue(loadedNotifications(makeNotification('one')))
    vi.mocked(api.getUnreadCount).mockResolvedValue({ count: 1 })
    vi.mocked(api.dismissNotification).mockResolvedValue()
    await store.fetch('district-one')
    await store.fetchUnreadCount('district-one')

    await store.dismiss('one')
    expect(api.dismissNotification).toHaveBeenCalledExactlyOnceWith('one')
    expect(store.items).toEqual([])
    expect(store.unreadCount).toBe(0)
    expect(store.total).toBe(0)

    await store.dismiss('one')
    expect(api.dismissNotification).toHaveBeenCalledTimes(1)
  })

  it('does not decrement the badge for an already-read notification', async () => {
    const store = prepareStore()
    vi.mocked(api.listNotifications).mockResolvedValue(loadedNotifications(makeNotification('read', '2026-09-30T08:01:00Z')))
    vi.mocked(api.getUnreadCount).mockResolvedValue({ count: 3 })
    vi.mocked(api.dismissNotification).mockResolvedValue()
    await store.fetch('district-one')
    await store.fetchUnreadCount('district-one')

    await store.dismiss('read')
    expect(store.unreadCount).toBe(3)
  })

  it('preserves the item and badge if dismissal fails', async () => {
    const store = prepareStore()
    vi.mocked(api.listNotifications).mockResolvedValue(loadedNotifications(makeNotification('one')))
    vi.mocked(api.getUnreadCount).mockResolvedValue({ count: 1 })
    vi.mocked(api.dismissNotification).mockRejectedValue(new Error('API unavailable'))
    await store.fetch('district-one')
    await store.fetchUnreadCount('district-one')

    await expect(store.dismiss('one')).rejects.toThrow('API unavailable')
    expect(store.items).toHaveLength(1)
    expect(store.unreadCount).toBe(1)
  })

  it('filters dismissed data defensively even when the server sends it', async () => {
    const store = prepareStore()
    vi.mocked(api.listNotifications).mockResolvedValue(loadedNotifications(
      makeNotification('visible'),
      { ...makeNotification('hidden'), dismissed_at: '2026-09-30T08:00:00Z' },
    ))
    await store.fetch('district-one')

    expect(store.items.map((item) => item.id)).toEqual(['visible'])
    expect(store.unreadItems).toHaveLength(1)
  })

  it('ignores stale responses from a previously selected district', async () => {
    const store = prepareStore()
    let resolveFirst!: (value: api.NotificationListResponse) => void
    vi.mocked(api.listNotifications)
      .mockImplementationOnce(() => new Promise((resolve) => { resolveFirst = resolve }))
      .mockResolvedValueOnce(loadedNotifications(makeNotification('current')))

    const oldRequest = store.fetch('district-one')
    await store.fetch('district-two')
    resolveFirst(loadedNotifications(makeNotification('stale')))
    await oldRequest

    expect(store.items.map((item) => item.id)).toEqual(['current'])
    expect(store.loading).toBe(false)
  })

  it('drops stale mutations when switching districts', async () => {
    const store = prepareStore()
    vi.mocked(api.listNotifications).mockResolvedValueOnce(loadedNotifications(makeNotification('old')))
      .mockResolvedValueOnce(loadedNotifications(makeNotification('new')))
    await store.fetch('district-one')
    let resolveDismiss!: () => void
    vi.mocked(api.dismissNotification).mockImplementation(() => new Promise((resolve) => { resolveDismiss = resolve }))

    const dismissal = store.dismiss('old')
    await store.fetch('district-two')
    resolveDismiss()
    await dismissal
    expect(store.items.map((item) => item.id)).toEqual(['new'])
  })

  it('marks visible notifications read without negative badge counts', async () => {
    const store = prepareStore()
    vi.mocked(api.listNotifications).mockResolvedValue(loadedNotifications(makeNotification('one')))
    vi.mocked(api.getUnreadCount).mockResolvedValue({ count: 1 })
    vi.mocked(api.markNotificationRead).mockResolvedValue()
    await store.fetch('district-one')
    await store.fetchUnreadCount('district-one')

    await store.markRead('one')
    await store.markRead('one')
    expect(api.markNotificationRead).toHaveBeenCalledTimes(1)
    expect(store.unreadCount).toBe(0)
  })

  it('does not clear the last known badge count after a failed poll', async () => {
    const store = prepareStore()
    vi.mocked(api.getUnreadCount).mockResolvedValueOnce({ count: 5 }).mockRejectedValueOnce(new Error('offline'))
    await store.fetchUnreadCount('district-one')
    await store.fetchUnreadCount('district-one')
    expect(store.unreadCount).toBe(5)
  })
})
