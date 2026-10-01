import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  listNotifications,
  getUnreadCount,
  markNotificationRead,
  dismissNotification,
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
  const activeDistrictId = ref<string | null>(null)
  let generation = 0

  const unreadItems = computed(() => items.value.filter((n) => !n.read_at && !n.dismissed_at))

  function selectDistrict(districtId: string) {
    if (activeDistrictId.value !== districtId) {
      activeDistrictId.value = districtId
      generation++
      items.value = []
      total.value = 0
      unreadCount.value = 0
      error.value = null
      loading.value = false
    }
  }

  async function fetch(districtId: string, options?: { unreadOnly?: boolean; limit?: number }) {
    selectDistrict(districtId)
    const requestGeneration = generation
    loading.value = true
    error.value = null
    try {
      const data: NotificationListResponse = await listNotifications(districtId, {
        unreadOnly: options?.unreadOnly,
        limit: options?.limit ?? 50,
      })
      if (requestGeneration !== generation) return
      items.value = data.items.filter((n) => !n.dismissed_at)
      total.value = data.total
    } catch (e) {
      if (requestGeneration !== generation) return
      error.value = e instanceof Error ? e.message : 'Fehler beim Laden der Benachrichtigungen'
    } finally {
      if (requestGeneration === generation) loading.value = false
    }
  }

  async function fetchUnreadCount(districtId: string) {
    selectDistrict(districtId)
    const requestGeneration = generation
    try {
      const data = await getUnreadCount(districtId)
      if (requestGeneration === generation) unreadCount.value = data.count
    } catch {
      // A failed poll must not hide the existing count or disrupt the UI.
    }
  }

  async function markRead(notificationId: string) {
    const target = items.value.find((n) => n.id === notificationId)
    if (!target || target.read_at || target.dismissed_at) return
    const requestGeneration = generation
    await markNotificationRead(notificationId)
    if (requestGeneration !== generation) return
    const current = items.value.find((n) => n.id === notificationId)
    if (current && !current.read_at && !current.dismissed_at) {
      current.read_at = new Date().toISOString()
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    }
  }

  async function dismiss(notificationId: string) {
    const target = items.value.find((n) => n.id === notificationId)
    if (!target || target.dismissed_at) return
    const requestGeneration = generation
    await dismissNotification(notificationId)
    if (requestGeneration !== generation) return
    const current = items.value.find((n) => n.id === notificationId)
    if (!current) return
    if (!current.read_at) unreadCount.value = Math.max(0, unreadCount.value - 1)
    items.value = items.value.filter((n) => n.id !== notificationId)
    total.value = Math.max(0, total.value - 1)
  }

  async function markAllRead(districtId: string) {
    selectDistrict(districtId)
    const requestGeneration = generation
    const result = await markAllNotificationsRead(districtId)
    if (requestGeneration !== generation) return
    const now = new Date().toISOString()
    items.value = items.value.map((n) =>
      n.read_at || n.dismissed_at ? n : { ...n, read_at: now },
    )
    unreadCount.value = Math.max(0, unreadCount.value - result.marked_read)
  }

  function startPolling(districtId: string, intervalMs = 60000) {
    stopPolling()
    selectDistrict(districtId)
    void fetchUnreadCount(districtId)
    pollIntervalRef.value = setInterval(() => {
      void fetchUnreadCount(districtId)
    }, intervalMs)
  }

  function stopPolling() {
    if (pollIntervalRef.value !== null) {
      clearInterval(pollIntervalRef.value)
      pollIntervalRef.value = null
    }
  }

  function reset() {
    stopPolling()
    generation++
    activeDistrictId.value = null
    items.value = []
    total.value = 0
    unreadCount.value = 0
    loading.value = false
    error.value = null
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
    dismiss,
    markAllRead,
    startPolling,
    stopPolling,
    reset,
  }
})
