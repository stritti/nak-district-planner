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
  const selectedDistrictId = ref('')
  const loading = ref(false)

  function ensureSelectedDistrict() {
    if (districts.value.length === 0) {
      selectedDistrictId.value = ''
      return
    }

    const selectedExists = districts.value.some((district) => district.id === selectedDistrictId.value)
    if (!selectedExists) {
      selectedDistrictId.value = districts.value[0].id
    }
  }

  function setSelectedDistrict(districtId: string) {
    selectedDistrictId.value = districtId
  }

  async function fetchDistricts() {
    loading.value = true
    try {
      districts.value = await listDistricts()
      ensureSelectedDistrict()
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
    selectedDistrictId,
    loading,
    ensureSelectedDistrict,
    setSelectedDistrict,
    fetchDistricts,
    fetchCongregations,
    fetchGroups,
    clearCongregations,
  }
}, {
  persist: { pick: ['selectedDistrictId'] },
})
