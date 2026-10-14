// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  createUnavailability,
  deleteUnavailability,
  listUnavailabilities,
  type LeaderUnavailabilityCreate,
  type LeaderUnavailabilityResponse,
} from '../api/leaderUnavailabilities'

type Mutation =
  | { generation: number; type: 'create'; item: LeaderUnavailabilityResponse }
  | { generation: number; type: 'delete'; id: string }

export const useLeaderUnavailabilitiesStore = defineStore('leaderUnavailabilities', () => {
  const items = ref<LeaderUnavailabilityResponse[]>([])
  const loading = ref(false)
  const currentDistrictId = ref('')
  let fetchGeneration = 0
  let mutationGeneration = 0
  const mutations: Mutation[] = []

  function sortItems(values: LeaderUnavailabilityResponse[]) {
    return [...values].sort((a, b) => Date.parse(a.start_at) - Date.parse(b.start_at))
  }

  function applyMutations(values: LeaderUnavailabilityResponse[], afterGeneration: number) {
    let reconciled = [...values]
    for (const mutation of mutations) {
      if (mutation.generation <= afterGeneration) continue
      if (mutation.type === 'create') {
        reconciled = [...reconciled.filter((item) => item.id !== mutation.item.id), mutation.item]
      } else {
        reconciled = reconciled.filter((item) => item.id !== mutation.id)
      }
    }
    return sortItems(reconciled)
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
      if (currentFetch === fetchGeneration && districtId === currentDistrictId.value) {
        items.value = applyMutations(result, mutationsAtStart)
      }
    } finally {
      if (currentFetch === fetchGeneration) loading.value = false
    }
  }

  async function addUnavailability(body: LeaderUnavailabilityCreate) {
    const districtId = currentDistrictId.value
    const created = await createUnavailability(districtId, body)
    if (currentDistrictId.value === districtId) {
      const generation = ++mutationGeneration
      mutations.push({ generation, type: 'create', item: created })
      items.value = applyMutations(items.value, generation - 1)
    }
    return created
  }

  async function removeUnavailability(unavailabilityId: string) {
    const districtId = currentDistrictId.value
    await deleteUnavailability(districtId, unavailabilityId)
    if (currentDistrictId.value === districtId) {
      const generation = ++mutationGeneration
      mutations.push({ generation, type: 'delete', id: unavailabilityId })
      items.value = applyMutations(items.value, generation - 1)
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
