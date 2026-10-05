import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useInvitationsStore } from './invitations'
import * as invitationApi from '../api/invitations'
import type { OverwriteRequestResponse } from '../api/invitations'

vi.mock('../api/invitations')

function overwriteRequest(id = 'req-1'): OverwriteRequestResponse {
  return {
    id,
    invitation_id: 'inv-1',
    source_event_id: 'src-1',
    source_event_title: 'Quelle',
    target_event_id: 'tgt-1',
    target_event_title: 'Ziel',
    target_congregation_id: 'cong-1',
    current_title: 'Alt',
    current_start_at: null,
    current_end_at: null,
    current_description: null,
    current_category: null,
    proposed_title: 'Neu',
    proposed_start_at: '2026-04-01T10:00:00Z',
    proposed_end_at: '2026-04-01T11:00:00Z',
    proposed_description: null,
    proposed_category: null,
    status: 'PENDING_OVERWRITE',
    decided_at: null,
    created_at: '2026-04-01T10:00:00Z',
    updated_at: '2026-04-01T10:00:00Z',
  }
}

describe('useInvitationsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(invitationApi.listOverwriteRequests).mockResolvedValue([])
    vi.mocked(invitationApi.decideOverwriteRequest).mockResolvedValue({
      ...overwriteRequest(),
      status: 'ACCEPTED',
    })
  })

  it('does not fetch without a district', async () => {
    const store = useInvitationsStore()
    await store.fetchForDistrict('')
    expect(invitationApi.listOverwriteRequests).not.toHaveBeenCalled()
  })

  it('fetches overwrite requests and clears a previous error', async () => {
    const item = overwriteRequest()
    vi.mocked(invitationApi.listOverwriteRequests).mockResolvedValue([item])
    const store = useInvitationsStore()
    store.error = 'old'

    await store.fetchForDistrict('district-1')

    expect(invitationApi.listOverwriteRequests).toHaveBeenCalledWith('district-1')
    expect(store.items).toEqual([item])
    expect(store.error).toBeNull()
    expect(store.loading).toBe(false)
  })

  it.each([
    [new Error('Laden fehlgeschlagen'), 'Laden fehlgeschlagen'],
    ['failure', 'Fehler beim Laden von Ueberschreibungsanfragen'],
  ])('records load failures and always clears loading', async (failure, expected) => {
    vi.mocked(invitationApi.listOverwriteRequests).mockRejectedValueOnce(failure)
    const store = useInvitationsStore()

    await store.fetchForDistrict('district-1')

    expect(store.error).toBe(expected)
    expect(store.loading).toBe(false)
  })

  it.each(['ACCEPTED', 'REJECTED'] as const)(
    'removes a request after a %s decision',
    async (decision) => {
      const store = useInvitationsStore()
      store.items = [overwriteRequest('req-1'), overwriteRequest('req-2')]

      await store.decide('req-1', decision)

      expect(invitationApi.decideOverwriteRequest).toHaveBeenCalledWith('req-1', decision)
      expect(store.items.map((item) => item.id)).toEqual(['req-2'])
    },
  )

  it('keeps the list unchanged when a decided request is no longer present', async () => {
    const store = useInvitationsStore()
    store.items = [overwriteRequest('req-2')]

    await store.decide('req-1', 'ACCEPTED')

    expect(store.items.map((item) => item.id)).toEqual(['req-2'])
  })
})
