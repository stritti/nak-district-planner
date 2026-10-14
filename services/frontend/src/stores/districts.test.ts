// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import * as districtsApi from '../api/districts'
import { useDistrictsStore } from './districts'
import { useAuthStore } from './auth'

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
    expect(store.selectedDistrictId).toBe('d2')
    store.selectedDistrictId = 'missing' // Simulate a stale ID restored from a session.
    store.ensureSelectedDistrict()
    expect(store.selectedDistrictId).toBe('d1')
    expect(store.loading).toBe(false)
  })

  it('exposes one active district without a switch and switches only among accessible districts', async () => {
    const store = useDistrictsStore()
    store.districts = [{ id: 'd1', name: 'Tuttlingen' }] as districtsApi.DistrictResponse[]
    store.ensureSelectedDistrict()
    expect(store.selectedDistrict?.name).toBe('Tuttlingen')
    expect(store.canSwitchDistrict).toBe(false)
    store.setSelectedDistrict('foreign')
    expect(store.selectedDistrictId).toBe('d1')

    store.districts.push({ id: 'd2', name: 'Konstanz' } as districtsApi.DistrictResponse)
    expect(store.canSwitchDistrict).toBe(true)
    store.setSelectedDistrict('d2')
    expect(store.selectedDistrict?.name).toBe('Konstanz')
    store.setSelectedDistrict('foreign')
    expect(store.selectedDistrictId).toBe('d2')
    store.setSelectedDistrict('')
    expect(store.selectedDistrictId).toBe('')
  })

  it('clears districts and cached subresources on logout', () => {
    const auth = useAuthStore()
    auth.setToken({ accessToken: 'token', idToken: 'token', expiresAt: Date.now() / 1000 + 60 }, { sub: 'user-one' })
    const store = useDistrictsStore()
    store.districts = [{ id: 'd1', name: 'District 1' }] as districtsApi.DistrictResponse[]
    store.setSelectedDistrict('d1')
    store.congregations = [{ id: 'c1' }] as districtsApi.CongregationResponse[]
    store.groups = [{ id: 'g1' }] as districtsApi.CongregationGroupResponse[]
    auth.clearAuth()
    expect(store.districts).toEqual([])
    expect(store.selectedDistrictId).toBe('')
    expect(store.selectedDistrict).toBeNull()
    expect(store.canSwitchDistrict).toBe(false)
    expect(store.congregations).toEqual([])
    expect(store.groups).toEqual([])
  })

  it('ignores a delayed district response after identity changes', async () => {
    const auth = useAuthStore()
    auth.setToken({ accessToken: 'token', idToken: 'token', expiresAt: Date.now() / 1000 + 60 }, { sub: 'user-one' })
    const store = useDistrictsStore()
    let resolveRequest!: (value: districtsApi.DistrictResponse[]) => void
    vi.mocked(districtsApi.listDistricts).mockImplementationOnce(
      () => new Promise((resolve) => { resolveRequest = resolve }),
    )
    const pending = store.fetchDistricts()
    auth.setToken({ accessToken: 'new', idToken: 'new', expiresAt: Date.now() / 1000 + 60 }, { sub: 'user-two' })
    resolveRequest([{ id: 'foreign', name: 'Foreign' }] as districtsApi.DistrictResponse[])
    await pending
    expect(store.districts).toEqual([])
    expect(store.selectedDistrictId).toBe('')
    expect(store.loading).toBe(false)
  })

  it('drops a revoked district and clears inaccessible selections on reload', async () => {
    const store = useDistrictsStore()
    store.districts = [{ id: 'd1', name: 'Old' }] as districtsApi.DistrictResponse[]
    store.setSelectedDistrict('d1')
    vi.mocked(districtsApi.listDistricts).mockResolvedValue([{ id: 'd2', name: 'New' }] as districtsApi.DistrictResponse[])
    await store.fetchDistricts()
    expect(store.selectedDistrictId).toBe('d2')
    vi.mocked(districtsApi.listDistricts).mockResolvedValue([])
    await store.fetchDistricts()
    expect(store.selectedDistrictId).toBe('')
    expect(store.selectedDistrict).toBeNull()
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
