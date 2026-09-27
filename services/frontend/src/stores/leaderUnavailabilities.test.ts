import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useLeaderUnavailabilitiesStore } from './leaderUnavailabilities'
import * as unavailabilityApi from '../api/leaderUnavailabilities'

vi.mock('../api/leaderUnavailabilities')

const sampleUnavailability = {
  id: 'unavail-1',
  leader_id: 'leader-1',
  start_at: '2026-05-01T00:00:00.000Z',
  end_at: '2026-05-03T00:00:00.000Z',
  reason: 'URLAUB' as const,
  note: null,
  created_at: '2026-04-01T00:00:00.000Z',
  updated_at: '2026-04-01T00:00:00.000Z',
}

describe('useLeaderUnavailabilitiesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(unavailabilityApi.listUnavailabilities).mockResolvedValue([sampleUnavailability])
    vi.mocked(unavailabilityApi.createUnavailability).mockResolvedValue(sampleUnavailability)
  })

  it('fetches unavailabilities for a district', async () => {
    const store = useLeaderUnavailabilitiesStore()
    await store.fetchUnavailabilities('district-1')
    expect(unavailabilityApi.listUnavailabilities).toHaveBeenCalledWith('district-1', undefined)
    expect(store.items).toHaveLength(1)
    expect(store.districtId).toBe('district-1')
  })

  it('does nothing without a district id', async () => {
    const store = useLeaderUnavailabilitiesStore()
    await store.fetchUnavailabilities('')
    expect(unavailabilityApi.listUnavailabilities).not.toHaveBeenCalled()
  })

  it('adds a created unavailability and keeps the list sorted by start date', async () => {
    vi.mocked(unavailabilityApi.createUnavailability).mockResolvedValue({
      ...sampleUnavailability,
      id: 'unavail-2',
      start_at: '2026-04-01T00:00:00.000Z',
      end_at: '2026-04-02T00:00:00.000Z',
    })
    const store = useLeaderUnavailabilitiesStore()
    store.items = [sampleUnavailability]
    await store.addUnavailability('district-1', {
      leader_id: 'leader-1',
      start_at: '2026-04-01T00:00:00.000Z',
      end_at: '2026-04-02T00:00:00.000Z',
      reason: 'URLAUB',
    })
    expect(store.items.map((i) => i.id)).toEqual(['unavail-2', 'unavail-1'])
  })

  it('removes a deleted unavailability from the list', async () => {
    const store = useLeaderUnavailabilitiesStore()
    store.items = [sampleUnavailability]
    await store.removeUnavailability('district-1', 'unavail-1')
    expect(unavailabilityApi.deleteUnavailability).toHaveBeenCalledWith('district-1', 'unavail-1')
    expect(store.items).toHaveLength(0)
  })
})
