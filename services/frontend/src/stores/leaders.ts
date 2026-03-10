import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listLeaders, type LeaderResponse } from '@/api/leaders'

export const useLeadersStore = defineStore('leaders', () => {
  const leaders = ref<LeaderResponse[]>([])
  const loading = ref(false)
  const districtId = ref<string>('')

  async function fetchLeaders(newDistrictId: string) {
    if (!newDistrictId) return
    loading.value = true
    try {
      districtId.value = newDistrictId
      leaders.value = await listLeaders(newDistrictId)
    } finally {
      loading.value = false
    }
  }

  function activeLeaders(): LeaderResponse[] {
    return leaders.value.filter((l) => l.is_active)
  }

  return { leaders, loading, districtId, fetchLeaders, activeLeaders }
})
