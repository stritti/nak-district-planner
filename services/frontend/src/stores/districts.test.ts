import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import * as districtsApi from '../api/districts'
import { useDistrictsStore } from './districts'

vi.mock('../api/districts')

describe('useDistrictsStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  it('clears selection when no district exists', () => {
    const store = useDistrictsStore()
    store.setSelectedDistrict('stale')

    store.ensureSelectedDistrict()

    expect(store.selectedDistrictId).toBe('')
  })

  it('keeps an existing selection and otherwise selects the first district', async () => {
    vi.mocked(districtsApi.listDistricts).mockResolvedValue([
      { id: 'd1', name: 'District 1' },
      { id: 'd2', name: 'District 2' },
    ] as districtsApi.DistrictResponse[])
    const store = useDistrictsStore()
    store.setSelectedDistrict('d2')

    await store.fetchDistricts()
    expect(store.selectedDistrictId).toBe('d2')

    store.setSelectedDistrict('missing')
    store.ensureSelectedDistrict()
    expect(store.selectedDistrictId).toBe('d1')
    expect(store.loading).toBe(false)
  })

  it('loads congregations and groups and can clear both collections', async () => {
    const congregations = [{ id: 'c1', name: 'Congregation 1' }] as districtsApi.CongregationResponse[]
    const groups = [{ id: 'g1', name: 'Group 1' }] as districtsApi.CongregationGroupResponse[]
    vi.mocked(districtsApi.listCongregations).mockResolvedValue(congregations)
    vi.mocked(districtsApi.listGroups).mockResolvedValue(groups)
    const store = useDistrictsStore()

    await store.fetchCongregations('d1', 'g1')
    await store.fetchGroups('d1')

    expect(districtsApi.listCongregations).toHaveBeenCalledWith('d1', 'g1')
    expect(districtsApi.listGroups).toHaveBeenCalledWith('d1')
    expect(store.congregations).toEqual(congregations)
    expect(store.groups).toEqual(groups)

    store.clearCongregations()
    expect(store.congregations).toEqual([])
    expect(store.groups).toEqual([])
  })

  it('resets loading when district loading fails', async () => {
    vi.mocked(districtsApi.listDistricts).mockRejectedValue(new Error('load failed'))
    const store = useDistrictsStore()

    await expect(store.fetchDistricts()).rejects.toThrow('load failed')
    expect(store.loading).toBe(false)
  })
})
