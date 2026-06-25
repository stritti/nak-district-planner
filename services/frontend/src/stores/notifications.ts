import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  listNotifications,
  getUnreadCount,
  markNotificationRead,
  markAllNotificationsRead,
  type NotificationItem,
  type NotificationListResponse,
} from '../api/notifications'

export const useNotificationStore = defineStore('notifications', () => {
  const items = ref<NotificationItem[]>([])
  const total = ref(0)
  const unreadCount = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const pollIntervalRef = ref<ReturnType<typeof setInterval> | null>(null)

  const unreadItems = computed(() => items.value.filter((n) => !n.read_at))

  async function fetch(districtId: string, options?: { unreadOnly?: boolean; limit?: number }) {
    loading.value = true
    error.value = null
    try {
      const data: NotificationListResponse = await listNotifications(districtId, {
        unreadOnly: options?.unreadOnly,
        limit: options?.limit ?? 50,
      })
      items.value = data.items
      total.value = data.total
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Fehler beim Laden der Benachrichtigungen'
    } finally {
      loading.value = false
    }
  }

  async function fetchUnreadCount(districtId: string) {
    try {
      const data = await getUnreadCount(districtId)
      unreadCount.value = data.count
    } catch {
      // silent — poll failures shouldn't disrupt the UI
    }
  }

  async function markRead(notificationId: string) {
    await markNotificationRead(notificationId)
    // Optimistic local update
    const idx = items.value.findIndex((n) => n.id === notificationId)
    if (idx !== -1) {
      items.value[idx] = { ...items.value[idx], read_at: new Date().toISOString() }
    }
    if (unreadCount.value > 0) unreadCount.value--
  }

  async function markAllRead(districtId: string) {
    const result = await markAllNotificationsRead(districtId)
    items.value = items.value.map((n) =>
      n.read_at ? n : { ...n, read_at: new Date().toISOString() },
    )
    unreadCount.value = Math.max(0, unreadCount.value - result.marked_read)
  }

  function startPolling(districtId: string, intervalMs = 30000) {
    stopPolling()
    fetchUnreadCount(districtId)
    pollIntervalRef.value = setInterval(() => {
      fetchUnreadCount(districtId)
    }, intervalMs)
  }

  function stopPolling() {
    if (pollIntervalRef.value !== null) {
      clearInterval(pollIntervalRef.value)
      pollIntervalRef.value = null
    }
  }

  return {
    items,
    total,
    unreadCount,
    loading,
    error,
    unreadItems,
    fetch,
    fetchUnreadCount,
    markRead,
    markAllRead,
    startPolling,
    stopPolling,
  }
})
