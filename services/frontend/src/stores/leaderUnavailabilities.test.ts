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
    vi.clearAllMocks()
    setActivePinia(createPinia())
    vi.mocked(unavailabilityApi.listUnavailabilities).mockResolvedValue([sampleUnavailability])
    vi.mocked(unavailabilityApi.createUnavailability).mockResolvedValue(sampleUnavailability)
  })

  it('fetches unavailabilities for a district', async () => {
    const store = useLeaderUnavailabilitiesStore()
    await store.fetchUnavailabilities('district-1')
    expect(unavailabilityApi.listUnavailabilities).toHaveBeenCalledWith('district-1')
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
    await store.fetchUnavailabilities('district-1')
    await store.addUnavailability({
      leader_id: 'leader-1',
      start_at: '2026-04-01T00:00:00.000Z',
      end_at: '2026-04-02T00:00:00.000Z',
      reason: 'URLAUB',
    })
    expect(store.items.map((i) => i.id)).toEqual(['unavail-2', 'unavail-1'])
  })

  it('removes a deleted unavailability from the list', async () => {
    const store = useLeaderUnavailabilitiesStore()
    await store.fetchUnavailabilities('district-1')
    await store.removeUnavailability('unavail-1')
    expect(unavailabilityApi.deleteUnavailability).toHaveBeenCalledWith('district-1', 'unavail-1')
    expect(store.items).toHaveLength(0)
  })

  it('ignores stale responses and keeps the current request loading', async () => {
    let finish!: (value: typeof sampleUnavailability[]) => void
    vi.mocked(unavailabilityApi.listUnavailabilities).mockImplementationOnce(
      () => new Promise((resolve) => { finish = resolve }),
    )
    const store = useLeaderUnavailabilitiesStore()
    const oldRequest = store.fetchUnavailabilities('old')
    await store.fetchUnavailabilities('new')
    finish([])
    await oldRequest
    expect(store.districtId).toBe('new')
    expect(store.items).toEqual([sampleUnavailability])
    expect(store.loading).toBe(false)
  })

  it('does not let an older fetch overwrite a completed create', async () => {
    let finishFetch!: (value: typeof sampleUnavailability[]) => void
    vi.mocked(unavailabilityApi.listUnavailabilities).mockImplementationOnce(
      () => new Promise((resolve) => { finishFetch = resolve }),
    )
    vi.mocked(unavailabilityApi.createUnavailability).mockResolvedValueOnce({
      ...sampleUnavailability,
      id: 'unavail-created',
    })
    const store = useLeaderUnavailabilitiesStore()
    const fetchRequest = store.fetchUnavailabilities('district-1')
    const created = await store.addUnavailability({
      leader_id: 'leader-1',
      start_at: '2026-05-01T00:00:00.000Z',
      end_at: '2026-05-02T00:00:00.000Z',
      reason: 'URLAUB',
    })
    expect(created.id).toBe('unavail-created')
    expect(store.items.map((item) => item.id)).toEqual(['unavail-created'])
    finishFetch([])
    await fetchRequest
    expect(store.items.map((item) => item.id)).toEqual(['unavail-created'])
  })

  it('merges pre-existing rows from a pending fetch with a completed create', async () => {
    let finishFetch!: (value: typeof sampleUnavailability[]) => void
    vi.mocked(unavailabilityApi.listUnavailabilities).mockImplementationOnce(
      () => new Promise((resolve) => { finishFetch = resolve }),
    )
    vi.mocked(unavailabilityApi.createUnavailability).mockResolvedValueOnce({
      ...sampleUnavailability,
      id: 'unavail-created',
      start_at: '2026-04-01T00:00:00.000Z',
    })
    const store = useLeaderUnavailabilitiesStore()
    const fetchRequest = store.fetchUnavailabilities('district-1')
    await store.addUnavailability({
      leader_id: 'leader-1',
      start_at: '2026-04-01T00:00:00.000Z',
      end_at: '2026-04-02T00:00:00.000Z',
      reason: 'URLAUB',
    })
    finishFetch([sampleUnavailability])
    await fetchRequest
    expect(store.items.map((item) => item.id)).toEqual(['unavail-created', 'unavail-1'])
  })

  it('keeps a pending fetch valid when a create fails', async () => {
    let finishFetch!: (value: typeof sampleUnavailability[]) => void
    vi.mocked(unavailabilityApi.listUnavailabilities).mockImplementationOnce(
      () => new Promise((resolve) => { finishFetch = resolve }),
    )
    vi.mocked(unavailabilityApi.createUnavailability).mockRejectedValueOnce(new Error('create failed'))
    const store = useLeaderUnavailabilitiesStore()
    const fetchRequest = store.fetchUnavailabilities('district-1')
    await expect(store.addUnavailability({
      leader_id: 'leader-1',
      start_at: '2026-05-01T00:00:00.000Z',
      end_at: '2026-05-02T00:00:00.000Z',
      reason: 'URLAUB',
    })).rejects.toThrow('create failed')
    expect(store.loading).toBe(true)
    finishFetch([sampleUnavailability])
    await fetchRequest
    expect(store.items).toEqual([sampleUnavailability])
    expect(store.loading).toBe(false)
  })

  it('applies every successful overlapping mutation', async () => {
    let finishCreate!: (value: typeof sampleUnavailability) => void
    let finishDelete!: () => void
    vi.mocked(unavailabilityApi.createUnavailability).mockImplementationOnce(
      () => new Promise((resolve) => { finishCreate = resolve }),
    )
    vi.mocked(unavailabilityApi.deleteUnavailability).mockImplementationOnce(
      () => new Promise((resolve) => { finishDelete = resolve }),
    )
    const store = useLeaderUnavailabilitiesStore()
    await store.fetchUnavailabilities('district-1')
    const createRequest = store.addUnavailability({
      leader_id: 'leader-1',
      start_at: '2026-04-01T00:00:00.000Z',
      end_at: '2026-04-02T00:00:00.000Z',
      reason: 'URLAUB',
    })
    const deleteRequest = store.removeUnavailability('unavail-1')
    finishDelete()
    await deleteRequest
    finishCreate({ ...sampleUnavailability, id: 'unavail-created', start_at: '2026-04-01T00:00:00.000Z' })
    await createRequest
    expect(store.items.map((item) => item.id)).toEqual(['unavail-created'])
  })

  it('does not apply a create result after switching districts', async () => {
    let finishCreate!: (value: typeof sampleUnavailability) => void
    vi.mocked(unavailabilityApi.createUnavailability).mockImplementationOnce(
      () => new Promise((resolve) => { finishCreate = resolve }),
    )
    const store = useLeaderUnavailabilitiesStore()
    await store.fetchUnavailabilities('district-1')
    const createRequest = store.addUnavailability({
      leader_id: 'leader-1',
      start_at: '2026-05-01T00:00:00.000Z',
      end_at: '2026-05-02T00:00:00.000Z',
      reason: 'URLAUB',
    })
    await store.fetchUnavailabilities('district-2')
    finishCreate({ ...sampleUnavailability, id: 'unavail-created' })
    await createRequest
    expect(store.districtId).toBe('district-2')
    expect(store.items).toEqual([sampleUnavailability])
  })

  it('clears old data and loading after a fetch failure', async () => {
    const store = useLeaderUnavailabilitiesStore()
    await store.fetchUnavailabilities('district-1')
    vi.mocked(unavailabilityApi.listUnavailabilities).mockRejectedValueOnce(new Error('offline'))
    await expect(store.fetchUnavailabilities('district-2')).rejects.toThrow('offline')
    expect(store.items).toEqual([])
    expect(store.loading).toBe(false)
  })

  it('does not mutate the fetched array in place', async () => {
    const fetched = [sampleUnavailability]
    vi.mocked(unavailabilityApi.listUnavailabilities).mockResolvedValueOnce(fetched)
    const store = useLeaderUnavailabilitiesStore()
    await store.fetchUnavailabilities('district-1')
    store.removeUnavailability('unavail-1')
    expect(fetched).toHaveLength(1)
  })
})
