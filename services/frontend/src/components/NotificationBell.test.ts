// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import * as api from '../api/notifications'
import { useNotificationStore } from '../stores/notifications'
import NotificationBell from './NotificationBell.vue'

vi.mock('../api/notifications')

const candidateId = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
const notification = (type = 'SYSTEM', overrides: Partial<api.NotificationItem> = {}): api.NotificationItem => ({
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
  ...overrides,
})

function mountBell() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const wrapper = mount(NotificationBell, { props: { districtId: 'district-1' }, global: { plugins: [pinia] } })
  return { wrapper, store: useNotificationStore() }
}

function actionButton(wrapper: ReturnType<typeof mountBell>['wrapper'], text: string) {
  const button = wrapper.findAll('button').find((element) => element.text() === text)
  if (!button) throw new Error(`Button not found: ${text}`)
  return button
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

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('loads and displays an empty notification center', async () => {
    const { wrapper } = mountBell()
    await wrapper.get('button[aria-controls="notification-center"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Keine Benachrichtigungen')
    wrapper.unmount()
  })

  it('shows the unread badge, marks one item read and dismisses it', async () => {
    vi.mocked(api.listNotifications).mockResolvedValue({ items: [notification()], total: 1, limit: 20, offset: 0 })
    vi.mocked(api.getUnreadCount).mockResolvedValue({ count: 1 })
    const { wrapper, store } = mountBell()
    await wrapper.get('button[aria-controls="notification-center"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Ein neues Ereignis')
    expect(store.unreadCount).toBe(1)

    await actionButton(wrapper, 'Gelesen').trigger('click')
    await flushPromises()
    expect(api.markNotificationRead).toHaveBeenCalledWith('notification-1')
    expect(store.unreadCount).toBe(0)

    await wrapper.get('button[aria-label="Ein neues Ereignis ausblenden"]').trigger('click')
    await flushPromises()
    expect(api.dismissNotification).toHaveBeenCalledWith('notification-1')
    expect(wrapper.text()).toContain('Keine Benachrichtigungen')
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
    await actionButton(wrapper, 'Ansehen').trigger('click')
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
    await actionButton(wrapper, 'Ansehen').trigger('click')
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
    await actionButton(wrapper, 'Alle gelesen').trigger('click')
    await flushPromises()
    expect(api.markAllNotificationsRead).toHaveBeenCalledWith('district-1')
    expect(store.unreadCount).toBe(0)
    wrapper.unmount()
  })

  it('reports a failed mark-all action', async () => {
    vi.mocked(api.listNotifications).mockResolvedValue({ items: [notification()], total: 1, limit: 20, offset: 0 })
    vi.mocked(api.getUnreadCount).mockResolvedValue({ count: 1 })
    vi.mocked(api.markAllNotificationsRead).mockRejectedValueOnce(new Error('offline'))
    const { wrapper } = mountBell()
    await wrapper.get('button[aria-controls="notification-center"]').trigger('click')
    await flushPromises()
    await actionButton(wrapper, 'Alle gelesen').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Aktion fehlgeschlagen')
    wrapper.unmount()
  })

  it('closes on Escape and when switching districts', async () => {
    const { wrapper } = mountBell()
    const bell = wrapper.get('button[aria-controls="notification-center"]')
    await bell.trigger('click')
    await flushPromises()
    expect(wrapper.find('#notification-center').exists()).toBe(true)

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await wrapper.vm.$nextTick()
    expect(wrapper.find('#notification-center').exists()).toBe(false)

    await bell.trigger('click')
    await flushPromises()
    await wrapper.setProps({ districtId: 'district-2' })
    await wrapper.vm.$nextTick()
    expect(wrapper.find('#notification-center').exists()).toBe(false)
    wrapper.unmount()
  })

  it('formats recent, hourly, daily, weekly and invalid timestamps', async () => {
    const now = new Date('2026-10-05T12:00:00Z').getTime()
    vi.spyOn(Date, 'now').mockReturnValue(now)
    vi.mocked(api.listNotifications).mockResolvedValue({
      items: [
        notification('SYSTEM', { id: 'n0', title: 'Invalid', created_at: 'invalid' }),
        notification('SYSTEM', { id: 'n1', title: 'Now', created_at: '2026-10-05T12:00:00Z' }),
        notification('SYSTEM', { id: 'n2', title: 'Minutes', created_at: '2026-10-05T11:55:00Z' }),
        notification('SYSTEM', { id: 'n3', title: 'Hours', created_at: '2026-10-05T09:00:00Z' }),
        notification('SYSTEM', { id: 'n4', title: 'Days', created_at: '2026-10-03T12:00:00Z' }),
        notification('SYSTEM', { id: 'n5', title: 'Old', created_at: '2026-09-20T12:00:00Z' }),
      ],
      total: 6,
      limit: 20,
      offset: 0,
    })
    const { wrapper } = mountBell()
    await wrapper.get('button[aria-controls="notification-center"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Gerade eben')
    expect(wrapper.text()).toContain('Vor 5 Min.')
    expect(wrapper.text()).toContain('Vor 3 Std.')
    expect(wrapper.text()).toContain('Vor 2 Tagen')
    expect(wrapper.text()).toContain('20.09.')
    wrapper.unmount()
  })
})
