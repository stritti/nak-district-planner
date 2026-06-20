<template>
  <div class="rounded-lg border p-4 shadow-sm" :class="borderClass">
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0 flex-1">
        <!-- Header -->
        <div class="flex items-center gap-2">
          <span
            class="inline-block h-2.5 w-2.5 rounded-full shrink-0"
            :class="statusDotClass"
            aria-hidden="true"
          />
          <span class="font-medium text-gray-900 dark:text-gray-100 truncate">
            {{ integration.name }}
          </span>
          <span class="badge text-xs" :class="typeBadgeClass">
            {{ integration.type }}
          </span>
        </div>

        <!-- Details -->
        <div class="mt-2 space-y-1 text-xs text-gray-500 dark:text-gray-400">
          <div v-if="lastSyncLabel" class="flex items-center gap-1.5">
            <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 6v6l4 2" />
            </svg>
            {{ lastSyncLabel }}
          </div>
          <div class="flex items-center gap-1.5">
            <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
              <path d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
            </svg>
            Sync alle {{ integration.sync_interval }} Minuten
          </div>
        </div>

        <!-- Error message -->
        <div
          v-if="errorMessage"
          class="mt-2 flex items-start gap-1.5 rounded bg-red-50 p-2 text-xs text-red-700 dark:bg-red-900/20 dark:text-red-300"
        >
          <svg class="mt-0.5 h-3.5 w-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
            <path d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
          </svg>
          <span>{{ errorMessage }}</span>
        </div>

        <!-- Sync result -->
        <div
          v-if="syncResult"
          class="mt-2 text-xs text-gray-600 dark:text-gray-400"
        >
          Letzter Sync: +{{ syncResult.created }} neu · ~{{ syncResult.updated }} aktualisiert ·
          ✕{{ syncResult.cancelled }} abgesagt
        </div>
      </div>

      <!-- Sync button -->
      <button
        class="shrink-0 flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50"
        :class="isSyncing
          ? 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-900/20 dark:text-blue-300'
          : 'border-gray-300 text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800'"
        :disabled="isSyncing || !integration.is_active"
        :aria-label="`Synchronisierung für ${integration.name} starten`"
        :title="integration.is_active ? 'Jetzt synchronisieren' : 'Integration ist inaktiv'"
        @click="$emit('sync', integration.id)"
      >
        <svg
          class="h-3.5 w-3.5"
          :class="{ 'animate-spin': isSyncing }"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          aria-hidden="true"
        >
          <path d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
        </svg>
        <span>{{ isSyncing ? 'Läuft…' : 'Sync' }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { CalendarIntegrationResponse, SyncResult, CalendarType } from '../api/calendarIntegrations'

const props = defineProps<{
  integration: CalendarIntegrationResponse
  isSyncing: boolean
  syncResult?: SyncResult | null
  syncError?: string | null
}>()

defineEmits<{
  sync: [integrationId: string]
}>()

const borderClass = computed(() => {
  if (props.syncError) return 'border-red-200 dark:border-red-800'
  if (props.isSyncing) return 'border-blue-200 dark:border-blue-800'
  if (props.integration.is_active) return 'border-gray-200 dark:border-gray-700'
  return 'border-gray-200 dark:border-gray-700 opacity-60'
})

const statusDotClass = computed(() => {
  if (props.isSyncing) return 'bg-blue-500 animate-pulse'
  if (props.syncError) return 'bg-red-500'
  if (props.integration.last_synced_at) return 'bg-green-500'
  return 'bg-gray-400'
})

const typeBadgeClass = computed(() => {
  const map: Record<CalendarType, string> = {
    ICS: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    CALDAV: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
    GOOGLE: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
    MICROSOFT: 'bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300',
  }
  return map[props.integration.type]
})

const lastSyncLabel = computed(() => {
  const last = props.integration.last_synced_at
  if (!last) return null
  const diff = Date.now() - new Date(last).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return 'Gerade eben synchronisiert'
  if (minutes < 60) return `Vor ${minutes} Min. synchronisiert`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `Vor ${hours} Std. synchronisiert`
  const days = Math.floor(hours / 24)
  return `Vor ${days} Tagen synchronisiert`
})

const errorMessage = computed(() => {
  if (!props.syncError) return null
  // Truncate long error messages
  return props.syncError.length > 120
    ? props.syncError.substring(0, 120) + '…'
    : props.syncError
})
</script>
