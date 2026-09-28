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
  const currentDistrictId = ref('')
  let requestId = 0

  function sortItems(values: LeaderUnavailabilityResponse[]) {
    return [...values].sort((a, b) => Date.parse(a.start_at) - Date.parse(b.start_at))
  }

  async function fetchUnavailabilities(districtId: string) {
    const currentRequest = ++requestId
    currentDistrictId.value = districtId
    items.value = []
    if (!districtId) {
      loading.value = false
      return
    }
    loading.value = true
    try {
      const result = await listUnavailabilities(districtId)
      if (currentRequest === requestId) items.value = sortItems(result)
    } finally {
      if (currentRequest === requestId) loading.value = false
    }
  }

  async function addUnavailability(body: LeaderUnavailabilityCreate) {
    const districtId = currentDistrictId.value
    const mutationRequest = ++requestId
    loading.value = false
    const created = await createUnavailability(districtId, body)
    if (currentDistrictId.value === districtId && mutationRequest === requestId) {
      items.value = sortItems([...items.value.filter((item) => item.id !== created.id), created])
    }
    return created
  }

  async function removeUnavailability(unavailabilityId: string) {
    const districtId = currentDistrictId.value
    const mutationRequest = ++requestId
    loading.value = false
    await deleteUnavailability(districtId, unavailabilityId)
    if (currentDistrictId.value === districtId && mutationRequest === requestId) {
      items.value = items.value.filter((item) => item.id !== unavailabilityId)
    }
  }

  return {
    items,
    loading,
    districtId: currentDistrictId,
    fetchUnavailabilities,
    addUnavailability,
    removeUnavailability,
  }
})
