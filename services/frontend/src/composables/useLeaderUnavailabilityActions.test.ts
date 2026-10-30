// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useLeaderUnavailabilitiesStore } from '../stores/leaderUnavailabilities'
import type { LeaderResponse } from '../api/leaders'
import { useLeaderUnavailabilityActions } from './useLeaderUnavailabilityActions'

const DISTRICT = 'dist-1'
const LEADER_ID = 'leader-1'

function leaderSnapshot(): LeaderResponse[] {
  return [{
    id: LEADER_ID,
    district_id: DISTRICT,
    name: 'Muster',
    active: true,
    rank: null,
    special_roles: [],
    assignments: [],
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }] as unknown as LeaderResponse[]
}

function leaderNameFromId(id: string): string {
  return `Name(${id})`
}

function setup(isSuperadmin: boolean) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const authStore = useAuthStore()
  authStore.isSuperadmin = isSuperadmin
  const unavailabilitiesStore = useLeaderUnavailabilitiesStore()
  vi.spyOn(unavailabilitiesStore, 'addUnavailability').mockResolvedValue({
    id: 'u1',
    leader_id: LEADER_ID,
    starts_at: '2026-05-01T00:00:00Z',
    ends_at: '2026-05-02T00:00:00Z',
    reason: null,
    created_at: '2026-01-01T00:00:00Z',
  } as never)
  vi.spyOn(unavailabilitiesStore, 'removeUnavailability').mockResolvedValue(undefined as never)

  const selectedDistrictId = ref(DISTRICT)
  const leaders = ref<LeaderResponse[]>(leaderSnapshot())
  const actions = useLeaderUnavailabilityActions(selectedDistrictId, leaders, leaderNameFromId)
  return { actions, unavailabilitiesStore }
}

describe('useLeaderUnavailabilityActions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('allows management for superadmins', () => {
    const { actions } = setup(true)
    expect(actions.canManageUnavailabilities.value).toBe(true)
  })

  it('denies management without matching district membership', () => {
    const { actions } = setup(false)
    expect(actions.canManageUnavailabilities.value).toBe(false)
  })

  it('saves an unavailability and resets the form on success', async () => {
    const { actions, unavailabilitiesStore } = setup(true)
    const reset = vi.fn()

    await actions.saveUnavailability({
      leader_id: LEADER_ID,
      starts_at: '2026-05-01',
      ends_at: '2026-05-02',
      reason: null,
    } as never, reset)

    expect(unavailabilitiesStore.addUnavailability).toHaveBeenCalledOnce()
    expect(reset).toHaveBeenCalledOnce()
    expect(actions.unavailabilitySavingDistrictId.value).toBe('')
  })

  it('skips saving without a selected district or permission', async () => {
    const { actions, unavailabilitiesStore } = setup(false)

    await actions.saveUnavailability({
      leader_id: LEADER_ID,
      starts_at: '2026-05-01',
      ends_at: '2026-05-02',
      reason: null,
    } as never)

    expect(unavailabilitiesStore.addUnavailability).not.toHaveBeenCalled()
  })

  it('keeps the saving district cleared when the store rejects', async () => {
    const { actions, unavailabilitiesStore } = setup(true)
    vi.spyOn(unavailabilitiesStore, 'addUnavailability').mockRejectedValue(new Error('boom'))

    await actions.saveUnavailability({
      leader_id: LEADER_ID,
      starts_at: '2026-05-01',
      ends_at: '2026-05-02',
      reason: null,
    } as never)

    expect(actions.unavailabilitySavingDistrictId.value).toBe('')
  })

  it('confirms and executes a delete, clearing the pending item', async () => {
    const { actions, unavailabilitiesStore } = setup(true)
    const item = { id: 'u1', leader_id: LEADER_ID, starts_at: '2026-05-01', ends_at: '2026-05-02' }

    actions.confirmDeleteUnavailability(item as never)
    expect(actions.pendingDeleteUnavailability.value?.id).toBe(item.id)

    await actions.executeDeleteUnavailability()
    expect(unavailabilitiesStore.removeUnavailability).toHaveBeenCalledWith('u1')
    expect(actions.pendingDeleteUnavailability.value).toBeNull()
    expect(actions.unavailabilityDeleting.value).toBe(false)
  })

  it('ignores deletes without a pending item', async () => {
    const { actions, unavailabilitiesStore } = setup(true)
    await actions.executeDeleteUnavailability()
    expect(unavailabilitiesStore.removeUnavailability).not.toHaveBeenCalled()
  })

  it('surfaces a failing delete without losing the pending item', async () => {
    const { actions, unavailabilitiesStore } = setup(true)
    vi.spyOn(unavailabilitiesStore, 'removeUnavailability').mockRejectedValue(new Error('boom'))
    actions.confirmDeleteUnavailability({ id: 'u1' } as never)

    await actions.executeDeleteUnavailability()

    expect(actions.pendingDeleteUnavailability.value).not.toBeNull()
    expect(actions.unavailabilityDeleting.value).toBe(false)
  })
})
