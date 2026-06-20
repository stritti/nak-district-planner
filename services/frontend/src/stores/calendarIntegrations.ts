import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listIntegrations,
  triggerSync,
  type CalendarIntegrationResponse,
  type SyncResult,
} from '../api/calendarIntegrations'

export const useCalendarIntegrationsStore = defineStore('calendarIntegrations', () => {
  const integrations = ref<CalendarIntegrationResponse[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const syncingId = ref<string | null>(null)
  const syncResults = ref<Record<string, SyncResult>>({})
  const syncErrors = ref<Record<string, string>>({})

  async function fetchIntegrations(districtId?: string) {
    loading.value = true
    error.value = null
    try {
      const res = await listIntegrations(districtId)
      integrations.value = res.items
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Fehler beim Laden'
    } finally {
      loading.value = false
    }
  }

  async function triggerIntegrationSync(id: string) {
    syncingId.value = id
    delete syncErrors.value[id]
    try {
      const result = await triggerSync(id)
      syncResults.value[id] = result
      // Refresh to get updated last_synced_at
      await fetchIntegrations()
      return result
    } catch (e) {
      syncErrors.value[id] = e instanceof Error ? e.message : 'Sync fehlgeschlagen'
      return null
    } finally {
      syncingId.value = null
    }
  }

  function clearSyncError(id: string) {
    delete syncErrors.value[id]
  }

  return {
    integrations,
    loading,
    error,
    syncingId,
    syncResults,
    syncErrors,
    fetchIntegrations,
    triggerIntegrationSync,
    clearSyncError,
  }
})
