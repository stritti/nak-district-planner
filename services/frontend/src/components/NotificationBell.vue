<template>
  <div class="relative">
    <button
      class="btn-icon relative rounded-md text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800"
      :title="unreadCount > 0 ? `${unreadCount} ungelesene Benachrichtigungen` : 'Keine ungelesenen Benachrichtigungen'"
      :aria-label="`Benachrichtigungen${unreadCount > 0 ? ` (${unreadCount} ungelesen)` : ''}`"
      :aria-expanded="open"
      aria-controls="notification-center"
      @click.stop="toggleOpen"
    >
      <BellIcon class="h-5 w-5" />
      <span
        v-if="unreadCount > 0"
        class="absolute -top-0.5 -right-0.5 inline-flex min-w-[1.1rem] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white ring-2 ring-white dark:ring-gray-900"
      >
        {{ unreadCount > 99 ? '99+' : unreadCount }}
      </span>
    </button>

    <Transition
      enter-active-class="transition ease-out duration-100"
      enter-from-class="transform opacity-0 scale-95"
      enter-to-class="transform opacity-100 scale-100"
      leave-active-class="transition ease-in duration-75"
      leave-from-class="transform opacity-100 scale-100"
      leave-to-class="transform opacity-0 scale-95"
    >
      <section
        v-if="open"
        id="notification-center"
        aria-label="Benachrichtigungen"
        class="absolute right-0 mt-2 w-80 sm:w-96 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50 max-h-[70vh] flex flex-col"
      >
        <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-700 shrink-0">
          <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">Benachrichtigungen</h3>
          <div class="flex items-center gap-2">
            <button
              v-if="unreadCount > 0"
              class="text-xs text-blue-600 dark:text-blue-400 hover:underline"
              @click="handleMarkAllRead"
            >
              Alle gelesen
            </button>
            <button
              class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
              @click="open = false"
              aria-label="Schließen"
            >
              <XMarkIcon class="h-4 w-4" />
            </button>
          </div>
        </div>

        <p v-if="error || actionError" role="alert" class="px-4 py-2 text-xs text-red-600">
          {{ actionError || error }}
        </p>

        <div class="overflow-y-auto flex-1">
          <div v-if="loading" class="flex items-center justify-center py-8" role="status" aria-label="Lade Benachrichtigungen">
            <div class="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
          <div v-else-if="items.length === 0" class="py-8 text-center text-sm text-gray-400 dark:text-gray-500">
            <BellSlashIcon class="h-8 w-8 mx-auto mb-2 opacity-50" />
            Keine Benachrichtigungen
          </div>
          <ul v-else>
            <li
              v-for="notification in items.slice(0, 20)"
              :key="notification.id"
              class="px-4 py-3 border-b border-gray-50 dark:border-gray-700/50 last:border-b-0"
              :class="{ 'bg-blue-50/50 dark:bg-blue-900/10': !notification.read_at }"
            >
              <div class="flex items-start gap-2">
                <div
                  class="mt-0.5 shrink-0 w-2 h-2 rounded-full"
                  :class="notification.read_at ? 'bg-transparent' : 'bg-blue-500'"
                />
                <div class="min-w-0 flex-1">
                  <p class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{{ notification.title }}</p>
                  <p v-if="notification.body" class="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">{{ notification.body }}</p>
                  <p class="text-[11px] text-gray-400 dark:text-gray-500 mt-1">{{ formatTime(notification.created_at) }}</p>
                  <div class="flex gap-3 mt-2">
                    <button
                      v-if="notificationDestination(notification)"
                      class="text-xs text-blue-600 hover:underline"
                      :disabled="busyIds.has(notification.id)"
                      @click="handleView(notification)"
                    >Ansehen</button>
                    <button
                      v-if="!notification.read_at"
                      class="text-xs text-gray-600 hover:underline"
                      :disabled="busyIds.has(notification.id)"
                      @click="handleMarkRead(notification)"
                    >Gelesen</button>
                    <button
                      class="text-xs text-gray-600 hover:underline disabled:opacity-50"
                      :disabled="busyIds.has(notification.id)"
                      :aria-label="`${notification.title} ausblenden`"
                      @click="handleDismiss(notification)"
                    >Ausblenden</button>
                  </div>
                </div>
              </div>
            </li>
          </ul>
        </div>
      </section>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { onUnmounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { BellIcon, BellSlashIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { useNotificationStore } from '../stores/notifications'
import { notificationDestination } from '../utils/notificationLinks'
import type { NotificationItem } from '../api/notifications'

const props = defineProps<{ districtId: string }>()
const emit = defineEmits<{
  (e: 'notification-click', notification: NotificationItem): void
}>()
const store = useNotificationStore()
const { items, unreadCount, loading, error } = storeToRefs(store)
const open = ref(false)
const actionError = ref<string | null>(null)
const busyIds = ref(new Set<string>())

function toggleOpen() {
  open.value = !open.value
  if (open.value) {
    actionError.value = null
    void store.fetch(props.districtId, { limit: 20 })
    void store.fetchUnreadCount(props.districtId)
  }
}

async function executeAction(id: string, action: () => Promise<void>): Promise<boolean> {
  if (busyIds.value.has(id)) return false
  busyIds.value = new Set([...busyIds.value, id])
  actionError.value = null
  try {
    await action()
    return true
  } catch {
    actionError.value = 'Aktion fehlgeschlagen. Bitte erneut versuchen.'
    return false
  } finally {
    const next = new Set(busyIds.value)
    next.delete(id)
    busyIds.value = next
  }
}

async function handleMarkRead(notification: NotificationItem) {
  await executeAction(notification.id, () => store.markRead(notification.id))
}

async function handleDismiss(notification: NotificationItem) {
  await executeAction(notification.id, () => store.dismiss(notification.id))
}

async function handleView(notification: NotificationItem) {
  if (!notificationDestination(notification)) return
  if (!notification.read_at) {
    const success = await executeAction(notification.id, () => store.markRead(notification.id))
    if (!success) return
  }
  open.value = false
  emit('notification-click', notification)
}

async function handleMarkAllRead() {
  actionError.value = null
  try {
    await store.markAllRead(props.districtId)
  } catch {
    actionError.value = 'Aktion fehlgeschlagen. Bitte erneut versuchen.'
  }
}

function formatTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  const diffMin = Math.max(0, Math.floor((Date.now() - date.getTime()) / 60000))
  if (diffMin < 1) return 'Gerade eben'
  if (diffMin < 60) return `Vor ${diffMin} Min.`
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return `Vor ${diffH} Std.`
  const diffD = Math.floor(diffH / 24)
  if (diffD < 7) return `Vor ${diffD} Tagen`
  return date.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' })
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') open.value = false
}

watch(open, (isOpen) => {
  if (isOpen) document.addEventListener('keydown', handleKeydown)
  else document.removeEventListener('keydown', handleKeydown)
})
watch(() => props.districtId, () => {
  open.value = false
  actionError.value = null
})
onUnmounted(() => document.removeEventListener('keydown', handleKeydown))
</script>
