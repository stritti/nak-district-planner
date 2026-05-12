import { defineStore } from 'pinia'
import { ref } from 'vue'

import {
  decideOverwriteRequest,
  listOverwriteRequests,
  type OverwriteRequestResponse,
} from '../api/invitations'

export const useInvitationsStore = defineStore('invitations', () => {
  const items = ref<OverwriteRequestResponse[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchForDistrict(districtId: string) {
    if (!districtId) return
    loading.value = true
    error.value = null
    try {
      items.value = await listOverwriteRequests(districtId)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Fehler beim Laden von Ueberschreibungsanfragen'
    } finally {
      loading.value = false
    }
  }

  async function decide(requestId: string, decision: 'ACCEPTED' | 'REJECTED') {
    await decideOverwriteRequest(requestId, decision)
    const idx = items.value.findIndex((item) => item.id === requestId)
    if (idx !== -1) {
      items.value.splice(idx, 1)
    }
  }

  return { items, loading, error, fetchForDistrict, decide }
})
