import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listCongregations,
  listDistricts,
  listGroups,
  type CongregationResponse,
  type DistrictResponse,
  type CongregationGroupResponse,
} from '@/api/districts'

export const useDistrictsStore = defineStore('districts', () => {
  const districts = ref<DistrictResponse[]>([])
  const congregations = ref<CongregationResponse[]>([])
  const groups = ref<CongregationGroupResponse[]>([])
  const loading = ref(false)

  async function fetchDistricts() {
    loading.value = true
    try {
      districts.value = await listDistricts()
    } finally {
      loading.value = false
    }
  }

  async function fetchCongregations(districtId: string, groupId?: string) {
    congregations.value = await listCongregations(districtId, groupId)
  }

  async function fetchGroups(districtId: string) {
    groups.value = await listGroups(districtId)
  }

  function clearCongregations() {
    congregations.value = []
    groups.value = []
  }

  return {
    districts,
    congregations,
    groups,
    loading,
    fetchDistricts,
    fetchCongregations,
    fetchGroups,
    clearCongregations,
  }
})
