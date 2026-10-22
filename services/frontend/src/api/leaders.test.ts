// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./client')

import * as client from './client'
import {
  addLeaderAssignment,
  createLeader,
  deleteLeader,
  getSelfLeaderLink,
  leaderDisplayName,
  leaderNameFromId,
  linkSelfToLeader,
  listLeaders,
  removeLeaderAssignment,
  unlinkSelfFromLeader,
  updateLeader,
  updateLeaderAssignment,
  updateLeaderInline,
  type LeaderResponse,
} from './leaders'

const apiFetch = vi.mocked(client.apiFetch)
const leader = (overrides: Partial<LeaderResponse> = {}): LeaderResponse => ({
  id: 'leader-1',
  name: 'Max Mustermann',
  district_id: 'district-1',
  rank: 'Pr.',
  assignments: [
    { id: 'a-1', congregation_id: 'congregation-1', role: null, is_home: true, revision: 'ar-1' },
  ],
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
    await updateLeader('district-1', 'leader-1', updateBody, '"leader-rev"')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/districts/district-1/leaders/leader-1', {
      method: 'PATCH',
      headers: { 'If-Match': '"leader-rev"' },
      body: JSON.stringify(updateBody),
    })

    await deleteLeader('district-1', 'leader-1')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/districts/district-1/leaders/leader-1', {
      method: 'DELETE',
    })
  })

  it('rejects blind leader edits', async () => {
    await expect(updateLeader('district-1', 'leader-1', { name: 'Bad' }, '')).rejects.toThrow('Versionsinformation')
    expect(apiFetch).not.toHaveBeenCalled()
  })

  it('requires the exact revision for inline leader contact edits', async () => {
    await updateLeaderInline('district-1', 'leader-1', { email: 'new@example.org' }, '"rev"')
    expect(apiFetch).toHaveBeenCalledWith('/api/v1/districts/district-1/leaders/leader-1/inline', {
      method: 'PATCH',
      headers: { 'If-Match': '"rev"' },
      body: JSON.stringify({ email: 'new@example.org' }),
    })
    apiFetch.mockClear()
    await expect(updateLeaderInline('district-1', 'leader-1', { email: null }, '')).rejects.toThrow('Versionsinformation')
    expect(apiFetch).not.toHaveBeenCalled()
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


describe('assignment requests', () => {
  beforeEach(() => apiFetch.mockReset())

  it('adds an assignment with a POST to the sub-resource', async () => {
    apiFetch.mockResolvedValue({ id: 'a-2' })
    await addLeaderAssignment('d1', 'l1', { congregation_id: 'c2', role: 'Gemeindevorsteher' })
    expect(apiFetch).toHaveBeenCalledWith('/api/v1/districts/d1/leaders/l1/assignments', {
      method: 'POST',
      body: JSON.stringify({ congregation_id: 'c2', role: 'Gemeindevorsteher' }),
    })
  })

  it('changes an assignment with the revision of that assignment', async () => {
    apiFetch.mockResolvedValue({ id: 'a-2' })
    await updateLeaderAssignment('d1', 'l1', 'a-2', { is_home: true }, '"r2"')
    expect(apiFetch).toHaveBeenCalledWith('/api/v1/districts/d1/leaders/l1/assignments/a-2', {
      method: 'PATCH',
      headers: { 'If-Match': '"r2"' },
      body: JSON.stringify({ is_home: true }),
    })
  })

  it('removes an assignment with the revision of that assignment', async () => {
    apiFetch.mockResolvedValue(undefined)
    await removeLeaderAssignment('d1', 'l1', 'a-2', '"r2"')
    expect(apiFetch).toHaveBeenCalledWith('/api/v1/districts/d1/leaders/l1/assignments/a-2', {
      method: 'DELETE',
      headers: { 'If-Match': '"r2"' },
    })
  })

  it('refuses to change or remove without a revision', async () => {
    await expect(updateLeaderAssignment('d1', 'l1', 'a-2', { role: null }, '')).rejects.toThrow('Versionsinformation')
    await expect(removeLeaderAssignment('d1', 'l1', 'a-2', '')).rejects.toThrow('Versionsinformation')
    expect(apiFetch).not.toHaveBeenCalled()
  })
})
