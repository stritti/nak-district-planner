import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
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
    vi.mocked(api.markNotificationRead).mockResolvedValue()
    vi.mocked(api.dismissNotification).mockResolvedValue()
    vi.mocked(api.markAllNotificationsRead).mockResolvedValue({ marked_read: 0 })
  })

  afterEach(() => vi.useRealTimers())

  it('loads, filters dismissed items and forwards list options', async () => {
    const store = prepareStore()
    vi.mocked(api.listNotifications).mockResolvedValue(loadedNotifications(
      makeNotification('visible'),
      { ...makeNotification('hidden'), dismissed_at: '2026-09-30T08:00:00Z' },
    ))

    await store.fetch('district-one', { unreadOnly: true, limit: 7 })

    expect(api.listNotifications).toHaveBeenCalledWith('district-one', {
      unreadOnly: true,
      limit: 7,
    })
    expect(store.items.map((item) => item.id)).toEqual(['visible'])
    expect(store.unreadItems).toHaveLength(1)
    expect(store.total).toBe(2)
    expect(store.loading).toBe(false)
  })

  it.each([
    [new Error('offline'), 'offline'],
    ['offline', 'Fehler beim Laden der Benachrichtigungen'],
  ])('records current-district fetch failures', async (failure, expected) => {
    vi.mocked(api.listNotifications).mockRejectedValueOnce(failure)
    const store = prepareStore()

    await store.fetch('district-one')

    expect(store.error).toBe(expected)
    expect(store.loading).toBe(false)
  })

  it('ignores stale success and error responses from a previous district', async () => {
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

    let rejectOld!: (reason: unknown) => void
    vi.mocked(api.listNotifications)
      .mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectOld = reject }))
      .mockResolvedValueOnce(loadedNotifications(makeNotification('current-2')))
    const staleFailure = store.fetch('district-one')
    await store.fetch('district-two')
    rejectOld(new Error('stale'))
    await staleFailure
    expect(store.error).toBeNull()
    expect(store.items.map((item) => item.id)).toEqual(['current-2'])
  })

  it('updates unread count, ignores failed polls and stale count responses', async () => {
    const store = prepareStore()
    vi.mocked(api.getUnreadCount).mockResolvedValueOnce({ count: 5 }).mockRejectedValueOnce(new Error('offline'))
    await store.fetchUnreadCount('district-one')
    await store.fetchUnreadCount('district-one')
    expect(store.unreadCount).toBe(5)

    let resolveOld!: (value: { count: number }) => void
    vi.mocked(api.getUnreadCount)
      .mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve }))
      .mockResolvedValueOnce({ count: 2 })
    const oldPoll = store.fetchUnreadCount('district-one')
    await store.fetchUnreadCount('district-two')
    resolveOld({ count: 99 })
    await oldPoll
    expect(store.unreadCount).toBe(2)
  })

  it('marks unread visible notifications read once and never goes negative', async () => {
    const store = prepareStore()
    vi.mocked(api.listNotifications).mockResolvedValue(loadedNotifications(makeNotification('one')))
    vi.mocked(api.getUnreadCount).mockResolvedValue({ count: 1 })
    await store.fetch('district-one')
    await store.fetchUnreadCount('district-one')

    await store.markRead('missing')
    await store.markRead('one')
    await store.markRead('one')

    expect(api.markNotificationRead).toHaveBeenCalledTimes(1)
    expect(store.items[0].read_at).not.toBeNull()
    expect(store.unreadCount).toBe(0)
  })

  it('does not mutate a mark-read result after switching districts', async () => {
    const store = prepareStore()
    vi.mocked(api.listNotifications)
      .mockResolvedValueOnce(loadedNotifications(makeNotification('old')))
      .mockResolvedValueOnce(loadedNotifications(makeNotification('new')))
    await store.fetch('district-one')
    let release!: () => void
    vi.mocked(api.markNotificationRead).mockImplementationOnce(() => new Promise(resolve => { release = resolve }))

    const pending = store.markRead('old')
    await store.fetch('district-two')
    release()
    await pending

    expect(store.items[0].id).toBe('new')
    expect(store.items[0].read_at).toBeNull()
  })

  it('dismisses unread and read notifications while preserving state on API failure', async () => {
    const store = prepareStore()
    vi.mocked(api.listNotifications).mockResolvedValue(loadedNotifications(
      makeNotification('unread'),
      makeNotification('read', '2026-09-30T08:01:00Z'),
    ))
    vi.mocked(api.getUnreadCount).mockResolvedValue({ count: 1 })
    await store.fetch('district-one')
    await store.fetchUnreadCount('district-one')

    await store.dismiss('missing')
    await store.dismiss('read')
    expect(store.unreadCount).toBe(1)
    await store.dismiss('unread')
    expect(store.unreadCount).toBe(0)
    expect(store.total).toBe(0)

    vi.mocked(api.listNotifications).mockResolvedValue(loadedNotifications(makeNotification('keep')))
    await store.fetch('district-one')
    vi.mocked(api.dismissNotification).mockRejectedValueOnce(new Error('API unavailable'))
    await expect(store.dismiss('keep')).rejects.toThrow('API unavailable')
    expect(store.items).toHaveLength(1)
  })

  it('drops stale dismiss mutations after switching districts', async () => {
    const store = prepareStore()
    vi.mocked(api.listNotifications)
      .mockResolvedValueOnce(loadedNotifications(makeNotification('old')))
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

  it('marks all eligible notifications read and subtracts only the reported count', async () => {
    const store = prepareStore()
    vi.mocked(api.listNotifications).mockResolvedValue(loadedNotifications(
      makeNotification('unread'),
      makeNotification('read', '2026-09-30T08:01:00Z'),
      { ...makeNotification('dismissed'), dismissed_at: '2026-09-30T08:02:00Z' },
    ))
    vi.mocked(api.getUnreadCount).mockResolvedValue({ count: 1 })
    vi.mocked(api.markAllNotificationsRead).mockResolvedValue({ marked_read: 5 })
    await store.fetch('district-one')
    await store.fetchUnreadCount('district-one')

    await store.markAllRead('district-one')

    expect(api.markAllNotificationsRead).toHaveBeenCalledWith('district-one')
    expect(store.items.every((item) => item.read_at || item.dismissed_at)).toBe(true)
    expect(store.unreadCount).toBe(0)
  })

  it('drops stale mark-all responses after switching districts', async () => {
    const store = prepareStore()
    vi.mocked(api.listNotifications)
      .mockResolvedValueOnce(loadedNotifications(makeNotification('old')))
      .mockResolvedValueOnce(loadedNotifications(makeNotification('new')))
    await store.fetch('district-one')
    let release!: (value: { marked_read: number }) => void
    vi.mocked(api.markAllNotificationsRead).mockImplementationOnce(() => new Promise(resolve => { release = resolve }))

    const pending = store.markAllRead('district-one')
    await store.fetch('district-two')
    release({ marked_read: 1 })
    await pending

    expect(store.items[0].id).toBe('new')
    expect(store.items[0].read_at).toBeNull()
  })

  it('starts, replaces and stops polling and reset clears state', async () => {
    vi.useFakeTimers()
    const store = prepareStore()
    vi.mocked(api.getUnreadCount).mockResolvedValue({ count: 3 })

    store.startPolling('district-one', 1000)
    await Promise.resolve()
    expect(api.getUnreadCount).toHaveBeenCalledWith('district-one')

    vi.advanceTimersByTime(1000)
    await Promise.resolve()
    expect(api.getUnreadCount).toHaveBeenCalledTimes(2)

    store.startPolling('district-two', 1000)
    store.error = 'old'
    store.items = [makeNotification('old')]
    store.total = 1
    store.unreadCount = 3
    store.reset()

    expect(store.items).toEqual([])
    expect(store.total).toBe(0)
    expect(store.unreadCount).toBe(0)
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })
})
