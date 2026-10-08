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
