// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { computed, ref, type Ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useLeaderUnavailabilitiesStore } from '../stores/leaderUnavailabilities'
import { useToastStore } from '../stores/toast'
import {
  formatUnavailabilityPeriod,
  type LeaderUnavailabilityCreate,
  type LeaderUnavailabilityResponse,
} from '../api/leaderUnavailabilities'
import type { LeaderResponse } from '../api/leaders'
import { userMessage } from '../api/errors'

export function useLeaderUnavailabilityActions(
  selectedDistrictId: Ref<string>,
  leaders: Ref<LeaderResponse[]>,
  leaderNameFromId: (id: string, snapshot: LeaderResponse[]) => string,
) {
  const authStore = useAuthStore()
  const unavailabilitiesStore = useLeaderUnavailabilitiesStore()
  const toastStore = useToastStore()

  const canManageUnavailabilities = computed(() => {
    if (authStore.isSuperadmin) return true
    return authStore.memberships.some(
      (membership) =>
        membership.scope_type === 'DISTRICT' &&
        membership.scope_id === selectedDistrictId.value &&
        ['PLANNER', 'CONGREGATION_ADMIN', 'DISTRICT_ADMIN'].includes(membership.role),
    )
  })

  const unavailabilitySavingDistrictId = ref('')
  const unavailabilityDeleting = ref(false)
  const pendingDeleteUnavailability = ref<LeaderUnavailabilityResponse | null>(null)

  async function saveUnavailability(body: LeaderUnavailabilityCreate, resetForm?: () => void) {
    const districtId = selectedDistrictId.value
    if (!districtId || !canManageUnavailabilities.value) return
    const leaderSnapshot = [...leaders.value]
    unavailabilitySavingDistrictId.value = districtId
    try {
      const created = await unavailabilitiesStore.addUnavailability(body)
      if (selectedDistrictId.value === districtId) {
        resetForm?.()
        toastStore.success(
          'Abwesenheit erfasst',
          `${leaderNameFromId(created.leader_id, leaderSnapshot)}: ${formatUnavailabilityPeriod(created)}`,
        )
      }
    } catch (e) {
      toastStore.error(
        'Abwesenheit konnte nicht erfasst werden',
        userMessage(e, 'Unbekannter Fehler'),
      )
    } finally {
      if (unavailabilitySavingDistrictId.value === districtId) unavailabilitySavingDistrictId.value = ''
    }
  }

  function confirmDeleteUnavailability(item: LeaderUnavailabilityResponse) {
    pendingDeleteUnavailability.value = item
  }

  async function executeDeleteUnavailability() {
    if (!pendingDeleteUnavailability.value || !selectedDistrictId.value || !canManageUnavailabilities.value) return
    const item = pendingDeleteUnavailability.value
    unavailabilityDeleting.value = true
    try {
      await unavailabilitiesStore.removeUnavailability(item.id)
      pendingDeleteUnavailability.value = null
      toastStore.success('Abwesenheit gelöscht', formatUnavailabilityPeriod(item))
    } catch (e) {
      toastStore.error('Löschen fehlgeschlagen', userMessage(e, 'Unbekannter Fehler'))
    } finally {
      unavailabilityDeleting.value = false
    }
  }

  return {
    unavailabilitySavingDistrictId,
    unavailabilityDeleting,
    pendingDeleteUnavailability,
    canManageUnavailabilities,
    saveUnavailability,
    confirmDeleteUnavailability,
    executeDeleteUnavailability,
  }
}
