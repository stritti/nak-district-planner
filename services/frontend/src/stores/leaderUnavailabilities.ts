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
  let fetchGeneration = 0
  let mutationGeneration = 0

  function sortItems(values: LeaderUnavailabilityResponse[]) {
    return [...values].sort((a, b) => Date.parse(a.start_at) - Date.parse(b.start_at))
  }

  async function fetchUnavailabilities(districtId: string) {
    const currentFetch = ++fetchGeneration
    const mutationsAtStart = mutationGeneration
    currentDistrictId.value = districtId
    items.value = []
    if (!districtId) {
      loading.value = false
      return
    }
    loading.value = true
    try {
      const result = await listUnavailabilities(districtId)
      if (
        currentFetch === fetchGeneration &&
        districtId === currentDistrictId.value &&
        mutationsAtStart === mutationGeneration
      ) {
        items.value = sortItems(result)
      }
    } finally {
      if (currentFetch === fetchGeneration) loading.value = false
    }
  }

  async function addUnavailability(body: LeaderUnavailabilityCreate) {
    const districtId = currentDistrictId.value
    const created = await createUnavailability(districtId, body)
    if (currentDistrictId.value === districtId) {
      mutationGeneration++
      items.value = sortItems([...items.value.filter((item) => item.id !== created.id), created])
    }
    return created
  }

  async function removeUnavailability(unavailabilityId: string) {
    const districtId = currentDistrictId.value
    await deleteUnavailability(districtId, unavailabilityId)
    if (currentDistrictId.value === districtId) {
      mutationGeneration++
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
