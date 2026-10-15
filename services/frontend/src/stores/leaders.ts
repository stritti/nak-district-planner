// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { listLeaders, type LeaderResponse } from '../api/leaders'

export const useLeadersStore = defineStore('leaders', () => {
  const leaders = ref<LeaderResponse[]>([])
  const loading = ref(false)
  const districtId = ref<string>('')

  let latestRequest = 0

  async function fetchLeaders(newDistrictId: string) {
    const request = ++latestRequest
    // Never label a previous district's choices as belonging to a pending request.
    districtId.value = ''
    leaders.value = []
    loading.value = !!newDistrictId
    if (!newDistrictId) return
    try {
      const loaded = await listLeaders(newDistrictId)
      if (request !== latestRequest) return
      leaders.value = loaded
      districtId.value = newDistrictId
    } finally {
      if (request === latestRequest) loading.value = false
    }
  }

  function activeLeaders(): LeaderResponse[] {
    return leaders.value.filter((l) => l.is_active)
  }

  const choices = computed(() => activeLeaders().map((leader) => ({
    value: leader.id,
    label: leader.rank ? `${leader.rank} ${leader.name}` : leader.name,
  })))

  function labelFor(leaderId: string | null): string | null {
    return choices.value.find((choice) => choice.value === leaderId)?.label ?? null
  }

  return { leaders, loading, districtId, fetchLeaders, activeLeaders, choices, labelFor }
})
