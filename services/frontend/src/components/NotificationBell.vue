<template>
  <div class="relative">
    <button
      class="relative p-2 rounded-md text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
      :title="unreadCount > 0 ? `${unreadCount} ungelesene Benachrichtigungen` : 'Keine ungelesenen Benachrichtigungen'"
      :aria-label="`Benachrichtigungen${unreadCount > 0 ? ` (${unreadCount} ungelesen)` : ''}`"
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

    <!-- Dropdown -->
    <Transition
      enter-active-class="transition ease-out duration-100"
      enter-from-class="transform opacity-0 scale-95"
      enter-to-class="transform opacity-100 scale-100"
      leave-active-class="transition ease-in duration-75"
      leave-from-class="transform opacity-100 scale-100"
      leave-to-class="transform opacity-0 scale-95"
    >
      <div
        v-if="open"
        class="absolute right-0 mt-2 w-80 sm:w-96 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50 max-h-[70vh] flex flex-col"
      >
        <!-- Header -->
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

        <!-- List -->
        <div class="overflow-y-auto flex-1">
          <div v-if="loading" class="flex items-center justify-center py-8">
            <div class="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>

          <div v-else-if="items.length === 0" class="py-8 text-center text-sm text-gray-400 dark:text-gray-500">
            <BellSlashIcon class="h-8 w-8 mx-auto mb-2 opacity-50" />
            Keine Benachrichtigungen
          </div>

          <template v-else>
            <button
              v-for="notification in items.slice(0, 20)"
              :key="notification.id"
              class="w-full text-left px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors border-b border-gray-50 dark:border-gray-700/50 last:border-b-0"
              :class="{ 'bg-blue-50/50 dark:bg-blue-900/10': !notification.read_at }"
              @click="handleClick(notification)"
            >
              <div class="flex items-start gap-2">
                <div
                  class="mt-0.5 shrink-0 w-2 h-2 rounded-full"
                  :class="notification.read_at ? 'bg-transparent' : 'bg-blue-500'"
                />
                <div class="min-w-0 flex-1">
                  <p class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                    {{ notification.title }}
                  </p>
                  <p v-if="notification.body" class="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">
                    {{ notification.body }}
                  </p>
                  <p class="text-[11px] text-gray-400 dark:text-gray-500 mt-1">
                    {{ formatTime(notification.created_at) }}
                  </p>
                </div>
              </div>
            </button>
          </template>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { BellIcon, BellSlashIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { useNotificationStore } from '../stores/notifications'

const props = defineProps<{
  districtId: string
}>()

const emit = defineEmits<{
  (e: 'notification-click', notification: { id: string; type: string; payload: Record<string, unknown> }): void
}>()

const store = useNotificationStore()
const open = ref(false)

const items = store.items
const unreadCount = store.unreadCount
const loading = store.loading

function toggleOpen() {
  open.value = !open.value
  if (open.value) {
    store.fetch(props.districtId, { limit: 20 })
    store.fetchUnreadCount(props.districtId)
  }
}

function handleClick(notification: { id: string; type: string; payload: Record<string, unknown>; read_at: string | null }) {
  if (!notification.read_at) {
    store.markRead(notification.id)
  }
  emit('notification-click', { id: notification.id, type: notification.type, payload: notification.payload })
}

async function handleMarkAllRead() {
  await store.markAllRead(props.districtId)
}

function formatTime(iso: string): string {
  const date = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)

  if (diffMin < 1) return 'Gerade eben'
  if (diffMin < 60) return `Vor ${diffMin} Min.`

  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return `Vor ${diffH} Std.`

  const diffD = Math.floor(diffH / 24)
  if (diffD < 7) return `Vor ${diffD} Tagen`

  return date.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' })
}

// Close on escape
watch(open, (isOpen) => {
  if (isOpen) {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') open.value = false
    }
    document.addEventListener('keydown', handler)
    const cleanup = () => document.removeEventListener('keydown', handler)
    // Cleanup when component unmounts or open closes
    const unwatch = watch(open, (val) => {
      if (!val) {
        cleanup()
        unwatch()
      }
    })
  }
})
</script>
