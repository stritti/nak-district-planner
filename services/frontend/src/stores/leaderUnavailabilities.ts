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

  async function fetchUnavailabilities(newDistrictId: string, leaderId?: string) {
    if (!newDistrictId) return
    loading.value = true
    try {
      districtId.value = newDistrictId
      items.value = await listUnavailabilities(newDistrictId, leaderId)
    } finally {
      loading.value = false
    }
  }

  async function addUnavailability(newDistrictId: string, body: LeaderUnavailabilityCreate) {
    const created = await createUnavailability(newDistrictId, body)
    items.value = [...items.value, created].sort((a, b) => a.start_at.localeCompare(b.start_at))
    return created
  }

  async function removeUnavailability(newDistrictId: string, unavailabilityId: string) {
    await deleteUnavailability(newDistrictId, unavailabilityId)
    items.value = items.value.filter((item) => item.id !== unavailabilityId)
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
