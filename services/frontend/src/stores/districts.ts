// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { useAuthStore } from './auth'
import { useSessionViewSettings, sessionField, sessionText } from '../composables/useSessionViewSettings'
import {
  listCongregations,
  listDistricts,
  listGroups,
  type CongregationResponse,
  type DistrictResponse,
  type CongregationGroupResponse,
} from '../api/districts'

export const useDistrictsStore = defineStore('districts', () => {
  const districts = ref<DistrictResponse[]>([])
  const congregations = ref<CongregationResponse[]>([])
  const groups = ref<CongregationGroupResponse[]>([])
  const selectedDistrictId = ref('')
  const loading = ref(false)
  const auth = useAuthStore()
  const selectedDistrict = computed(() =>
    districts.value.find((district) => district.id === selectedDistrictId.value) ?? null,
  )
  const canSwitchDistrict = computed(() => districts.value.length > 1)
  let fetchVersion = 0

  // An identity change or logout must invalidate in-flight requests and cached tenant data.
  watch(
    () => [auth.isAuthenticated, auth.user?.sub] as const,
    ([authenticated, identity], previous) => {
      if (!authenticated || (previous?.[1] && previous[1] !== identity)) {
        fetchVersion++
        districts.value = []
        selectedDistrictId.value = ''
        clearCongregations()
        loading.value = false
      }
    },
    { flush: 'sync' },
  )
  useSessionViewSettings('navigation', () => auth.user?.sub ?? null, () => 'district', {
    district: sessionField(selectedDistrictId, () => '', sessionText),
  })

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
    if (districtId && districts.value.length > 0 && !districts.value.some((district) => district.id === districtId)) {
      return
    }
    selectedDistrictId.value = districtId
  }

  async function fetchDistricts() {
    const version = ++fetchVersion
    const identity = auth.user?.sub
    loading.value = true
    try {
      const allowedDistricts = await listDistricts()
      if (version !== fetchVersion || identity !== auth.user?.sub) return
      districts.value = allowedDistricts
      ensureSelectedDistrict()
    } catch (error) {
      if (version === fetchVersion && identity === auth.user?.sub) {
        districts.value = []
        ensureSelectedDistrict()
      }
      throw error
    } finally {
      if (version === fetchVersion) loading.value = false
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
    selectedDistrict,
    canSwitchDistrict,
    loading,
    ensureSelectedDistrict,
    setSelectedDistrict,
    fetchDistricts,
    fetchCongregations,
    fetchGroups,
    clearCongregations,
  }
})
