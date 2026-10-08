import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  createIntegration,
  deleteIntegration,
  listIntegrations,
  triggerSync,
  updateIntegration,
  type CalendarIntegrationCreate,
  type CalendarIntegrationResponse,
  type CalendarIntegrationUpdate,
  type SyncResult,
} from '../api/calendarIntegrations'

export const useCalendarIntegrationsStore = defineStore('calendarIntegrations', () => {
  const integrations = ref<CalendarIntegrationResponse[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const syncingId = ref<string | null>(null)
  const syncResults = ref<Record<string, SyncResult>>({})
  const syncErrors = ref<Record<string, string>>({})
  const districtFilter = ref<string | undefined>(undefined)

  async function fetchIntegrations(districtId?: string) {
    districtFilter.value = districtId
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

  async function create(payload: CalendarIntegrationCreate) {
    const created = await createIntegration(payload)
    integrations.value.unshift(created)
    return created
  }

  async function update(id: string, payload: CalendarIntegrationUpdate) {
    const updated = await updateIntegration(id, payload)
    const index = integrations.value.findIndex((item) => item.id === id)
    if (index !== -1) integrations.value[index] = updated
    return updated
  }

  async function remove(id: string) {
    await deleteIntegration(id)
    integrations.value = integrations.value.filter((item) => item.id !== id)
  }

  async function triggerIntegrationSync(id: string) {
    syncingId.value = id
    delete syncErrors.value[id]
    try {
      const result = await triggerSync(id)
      syncResults.value[id] = result
      // Preserve the active district filter while refreshing last_synced_at.
      await fetchIntegrations(districtFilter.value)
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
    districtFilter,
    fetchIntegrations,
    create,
    update,
    remove,
    triggerIntegrationSync,
    clearSyncError,
  }
})
