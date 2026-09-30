import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import * as api from '../api/notifications'
import { useNotificationStore } from '../stores/notifications'
import NotificationBell from './NotificationBell.vue'

vi.mock('../api/notifications')

const candidateId = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
const notification = (type = 'SYSTEM'): api.NotificationItem => ({
  id: 'notification-1',
  district_id: 'district-1',
  congregation_id: null,
  type,
  title: 'Ein neues Ereignis',
  body: 'Prüfung erforderlich',
  payload: type === 'CANDIDATE_REVIEW' ? { candidate_id: candidateId } : {},
  read_at: null,
  dismissed_at: null,
  created_at: '2026-09-30T09:00:00Z',
})

function mountBell() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const wrapper = mount(NotificationBell, { props: { districtId: 'district-1' }, global: { plugins: [pinia] } })
  return { wrapper, store: useNotificationStore() }
}

describe('NotificationBell', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.listNotifications).mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 })
    vi.mocked(api.getUnreadCount).mockResolvedValue({ count: 0 })
    vi.mocked(api.markNotificationRead).mockResolvedValue()
    vi.mocked(api.dismissNotification).mockResolvedValue()
    vi.mocked(api.markAllNotificationsRead).mockResolvedValue({ marked_read: 1 })
  })

  it('loads and displays an empty notification center', async () => {
    const { wrapper } = mountBell()
    await wrapper.get('button[aria-controls="notification-center"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Keine Benachrichtigungen')
    wrapper.unmount()
  })

  it('shows the unread badge and dismisses an item', async () => {
    vi.mocked(api.listNotifications).mockResolvedValue({ items: [notification()], total: 1, limit: 20, offset: 0 })
    vi.mocked(api.getUnreadCount).mockResolvedValue({ count: 1 })
    const { wrapper, store } = mountBell()
    await wrapper.get('button[aria-controls="notification-center"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Ein neues Ereignis')
    expect(store.unreadCount).toBe(1)

    await wrapper.get('button[aria-label="Ein neues Ereignis ausblenden"]').trigger('click')
    await flushPromises()
    expect(api.dismissNotification).toHaveBeenCalledWith('notification-1')
    expect(wrapper.text()).toContain('Keine Benachrichtigungen')
    expect(store.unreadCount).toBe(0)
    wrapper.unmount()
  })

  it('keeps the notification visible and reports failed dismissals', async () => {
    vi.mocked(api.listNotifications).mockResolvedValue({ items: [notification()], total: 1, limit: 20, offset: 0 })
    vi.mocked(api.dismissNotification).mockRejectedValue(new Error('offline'))
    const { wrapper } = mountBell()
    await wrapper.get('button[aria-controls="notification-center"]').trigger('click')
    await flushPromises()
    await wrapper.get('button[aria-label="Ein neues Ereignis ausblenden"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Aktion fehlgeschlagen')
    expect(wrapper.text()).toContain('Ein neues Ereignis')
    wrapper.unmount()
  })

  it('exposes a deep link only for known references and marks viewed items read', async () => {
    vi.mocked(api.listNotifications).mockResolvedValue({ items: [notification('CANDIDATE_REVIEW')], total: 1, limit: 20, offset: 0 })
    const { wrapper } = mountBell()
    await wrapper.get('button[aria-controls="notification-center"]').trigger('click')
    await flushPromises()
    await wrapper.get('button').trigger('focus')
    await wrapper.get('button:text("Ansehen")').trigger('click')
    await flushPromises()
    expect(api.markNotificationRead).toHaveBeenCalledWith('notification-1')
    expect(wrapper.emitted('notification-click')).toHaveLength(1)
    expect(wrapper.find('#notification-center').exists()).toBe(false)
    wrapper.unmount()
  })

  it('does not navigate if marking the item read fails', async () => {
    vi.mocked(api.listNotifications).mockResolvedValue({ items: [notification('CANDIDATE_REVIEW')], total: 1, limit: 20, offset: 0 })
    vi.mocked(api.markNotificationRead).mockRejectedValue(new Error('offline'))
    const { wrapper } = mountBell()
    await wrapper.get('button[aria-controls="notification-center"]').trigger('click')
    await flushPromises()
    await wrapper.get('button:text("Ansehen")').trigger('click')
    await flushPromises()
    expect(wrapper.emitted('notification-click')).toBeUndefined()
    expect(wrapper.text()).toContain('Aktion fehlgeschlagen')
    wrapper.unmount()
  })

  it('marks all notifications read and updates the badge', async () => {
    vi.mocked(api.listNotifications).mockResolvedValue({ items: [notification()], total: 1, limit: 20, offset: 0 })
    vi.mocked(api.getUnreadCount).mockResolvedValue({ count: 1 })
    const { wrapper, store } = mountBell()
    await wrapper.get('button[aria-controls="notification-center"]').trigger('click')
    await flushPromises()
    await wrapper.get('button:text("Alle gelesen")').trigger('click')
    await flushPromises()
    expect(api.markAllNotificationsRead).toHaveBeenCalledWith('district-1')
    expect(store.unreadCount).toBe(0)
    wrapper.unmount()
  })
})
