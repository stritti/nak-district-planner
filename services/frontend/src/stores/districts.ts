import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listCongregations,
  listDistricts,
  type CongregationResponse,
  type DistrictResponse,
} from '@/api/districts'

export const useDistrictsStore = defineStore('districts', () => {
  const districts = ref<DistrictResponse[]>([])
  const congregations = ref<CongregationResponse[]>([])
  const loading = ref(false)

  async function fetchDistricts() {
    loading.value = true
    try {
      districts.value = await listDistricts()
    } finally {
      loading.value = false
    }
  }

  async function fetchCongregations(districtId: string) {
    congregations.value = await listCongregations(districtId)
  }

  function clearCongregations() {
    congregations.value = []
  }

  return { districts, congregations, loading, fetchDistricts, fetchCongregations, clearCongregations }
})
