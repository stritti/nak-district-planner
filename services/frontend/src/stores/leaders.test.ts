// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import * as leadersApi from '../api/leaders'
import { useLeadersStore } from './leaders'

vi.mock('../api/leaders')

const leader = (id: string, isActive: boolean): leadersApi.LeaderResponse => ({
  id,
  name: `Leader ${id}`,
  email: `${id}@example.org`,
  is_active: isActive,
  congregation_id: null,
  congregation_name: null,
  district_id: 'district-1',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
})

describe('useLeadersStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  it('does not call the API for an empty district', async () => {
    const store = useLeadersStore()

    await store.fetchLeaders('')

    expect(leadersApi.listLeaders).not.toHaveBeenCalled()
    expect(store.loading).toBe(false)
  })

  it('loads leaders for a district and exposes active leaders only', async () => {
    vi.mocked(leadersApi.listLeaders).mockResolvedValue([
      leader('active', true),
      leader('inactive', false),
    ])
    const store = useLeadersStore()

    await store.fetchLeaders('district-1')

    expect(leadersApi.listLeaders).toHaveBeenCalledWith('district-1')
    expect(store.districtId).toBe('district-1')
    expect(store.loading).toBe(false)
    expect(store.activeLeaders().map((item) => item.id)).toEqual(['active'])
  })

  it('always resets loading when the API fails', async () => {
    vi.mocked(leadersApi.listLeaders).mockRejectedValue(new Error('boom'))
    const store = useLeadersStore()

    await expect(store.fetchLeaders('district-1')).rejects.toThrow('boom')
    expect(store.loading).toBe(false)
  })
})


describe('Leader choice ownership', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())
  })

  it('clears previous choices while the next district is loading', async () => {
    const store = useLeadersStore()
    store.leaders = [leader('old', true)]
    store.districtId = 'district-1'
    let finish!: (items: leadersApi.LeaderResponse[]) => void
    vi.mocked(leadersApi.listLeaders).mockImplementation(() => new Promise((resolve) => { finish = resolve }))
    const pending = store.fetchLeaders('district-2')
    expect(store.districtId).toBe('')
    expect(store.choices).toEqual([])
    expect(store.loading).toBe(true)
    finish([{ ...leader('new', true), district_id: 'district-2', rank: 'Di.' }])
    await pending
    expect(store.districtId).toBe('district-2')
    expect(store.choices).toEqual([{ value: 'new', label: 'Di. Leader new' }])
    expect(store.labelFor('new')).toBe('Di. Leader new')
    expect(store.labelFor('unknown')).toBeNull()
  })

  it('ignores a slower response for a previously selected district', async () => {
    let finishFirst!: (items: leadersApi.LeaderResponse[]) => void
    vi.mocked(leadersApi.listLeaders)
      .mockImplementationOnce(() => new Promise((resolve) => { finishFirst = resolve }))
      .mockResolvedValueOnce([{ ...leader('second', true), district_id: 'district-2' }])
    const store = useLeadersStore()
    const first = store.fetchLeaders('district-1')
    await store.fetchLeaders('district-2')
    finishFirst([leader('first', true)])
    await first
    expect(store.districtId).toBe('district-2')
    expect(store.choices).toEqual([{ value: 'second', label: 'Leader second' }])
    expect(store.loading).toBe(false)
  })

  it('keeps a failed district load empty instead of exposing old choices', async () => {
    const store = useLeadersStore()
    store.leaders = [leader('old', true)]
    store.districtId = 'district-1'
    vi.mocked(leadersApi.listLeaders).mockRejectedValue(new Error('offline'))
    await expect(store.fetchLeaders('district-2')).rejects.toThrow('offline')
    expect(store.districtId).toBe('')
    expect(store.choices).toEqual([])
    expect(store.loading).toBe(false)
  })

  it('invalidates a pending response when the district selection is cleared', async () => {
    let finish!: (items: leadersApi.LeaderResponse[]) => void
    vi.mocked(leadersApi.listLeaders).mockImplementation(() => new Promise((resolve) => { finish = resolve }))
    const store = useLeadersStore()
    const pending = store.fetchLeaders('district-1')
    await store.fetchLeaders('')
    finish([leader('old', true)])
    await pending
    expect(store.districtId).toBe('')
    expect(store.choices).toEqual([])
    expect(store.loading).toBe(false)
  })
})
