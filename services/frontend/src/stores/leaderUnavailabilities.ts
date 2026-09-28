import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  createUnavailability,
  deleteUnavailability,
  listUnavailabilities,
  type LeaderUnavailabilityCreate,
  type LeaderUnavailabilityResponse,
} from '../api/leaderUnavailabilities'

export const useLeaderUnavailabilitiesStore = defineStore('leaderUnavailabilities', () => {
  const items = ref<LeaderUnavailabilityResponse[]>([])
  const loading = ref(false)
  const districtId = ref('')
  let requestId = 0
  let selectedLeaderId: string | undefined

  function sortItems(values: LeaderUnavailabilityResponse[]) {
    return values.sort((a, b) => Date.parse(a.start_at) - Date.parse(b.start_at))
  }

  async function fetchUnavailabilities(newDistrictId: string, leaderId?: string) {
    const currentRequest = ++requestId
    districtId.value = newDistrictId
    selectedLeaderId = leaderId
    items.value = []
    if (!newDistrictId) {
      loading.value = false
      return
    }
    loading.value = true
    try {
      const result = await listUnavailabilities(newDistrictId, leaderId)
      if (currentRequest === requestId) items.value = sortItems(result)
    } finally {
      if (currentRequest === requestId) loading.value = false
    }
  }

  async function addUnavailability(newDistrictId: string, body: LeaderUnavailabilityCreate) {
    const created = await createUnavailability(newDistrictId, body)
    if (districtId.value === newDistrictId && (!selectedLeaderId || selectedLeaderId === created.leader_id)) {
      items.value = sortItems([...items.value.filter((item) => item.id !== created.id), created])
    }
    return created
  }

  async function removeUnavailability(newDistrictId: string, unavailabilityId: string) {
    await deleteUnavailability(newDistrictId, unavailabilityId)
    if (districtId.value === newDistrictId) {
      items.value = items.value.filter((item) => item.id !== unavailabilityId)
    }
  }

  return {
    items,
    loading,
    districtId,
    fetchUnavailabilities,
    addUnavailability,
    removeUnavailability,
  }
})
