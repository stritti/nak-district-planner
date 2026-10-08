import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./client')

import * as client from './client'
import {
  createLeader,
  deleteLeader,
  getSelfLeaderLink,
  leaderDisplayName,
  leaderNameFromId,
  linkSelfToLeader,
  listLeaders,
  unlinkSelfFromLeader,
  updateLeader,
  type LeaderResponse,
} from './leaders'

const apiFetch = vi.mocked(client.apiFetch)
const leader = (overrides: Partial<LeaderResponse> = {}): LeaderResponse => ({
  id: 'leader-1',
  name: 'Max Mustermann',
  district_id: 'district-1',
  rank: 'Pr.',
  congregation_id: 'congregation-1',
  special_role: null,
  user_sub: null,
  email: null,
  phone: null,
  notes: null,
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  ...overrides,
})

describe('leader helpers', () => {
  it('formats ranked and unranked leaders', () => {
    expect(leaderDisplayName(leader())).toBe('Pr. Max Mustermann')
    expect(leaderDisplayName(leader({ rank: null }))).toBe('Max Mustermann')
  })

  it('looks up a leader name or returns the placeholder', () => {
    expect(leaderNameFromId('leader-1', [leader()])).toBe('Pr. Max Mustermann')
    expect(leaderNameFromId('missing', [leader()])).toBe('—')
  })
})

describe('leader API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiFetch.mockResolvedValue({})
  })

  it('lists, creates, updates and deletes leaders', async () => {
    await listLeaders('district-1')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/districts/district-1/leaders')

    const createBody = { name: 'Max', rank: 'Pr.' as const, is_active: true }
    await createLeader('district-1', createBody)
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/districts/district-1/leaders', {
      method: 'POST',
      body: JSON.stringify(createBody),
    })

    const updateBody = { name: 'Max Neu', rank: null }
    await updateLeader('district-1', 'leader-1', updateBody)
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/districts/district-1/leaders/leader-1', {
      method: 'PATCH',
      body: JSON.stringify(updateBody),
    })

    await deleteLeader('district-1', 'leader-1')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/districts/district-1/leaders/leader-1', {
      method: 'DELETE',
    })
  })

  it('covers self-link lifecycle', async () => {
    await getSelfLeaderLink('district-1')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/districts/district-1/leaders/link-self')

    await linkSelfToLeader('district-1', 'leader-1')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/districts/district-1/leaders/link-self', {
      method: 'POST',
      body: JSON.stringify({ leader_id: 'leader-1' }),
    })

    await unlinkSelfFromLeader('district-1')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/districts/district-1/leaders/link-self', {
      method: 'DELETE',
    })
  })
})
