import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useInvitationsStore } from './invitations'
import * as invitationApi from '@/api/invitations'

vi.mock('@/api/invitations')

describe('useInvitationsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(invitationApi.listOverwriteRequests).mockResolvedValue([])
    vi.mocked(invitationApi.decideOverwriteRequest).mockResolvedValue({
      id: 'req-1',
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
      status: 'ACCEPTED',
      decided_at: null,
      created_at: '2026-04-01T10:00:00Z',
      updated_at: '2026-04-01T10:00:00Z',
    })
  })

  it('fetches overwrite requests', async () => {
    const store = useInvitationsStore()
    await store.fetchForDistrict('district-1')
    expect(invitationApi.listOverwriteRequests).toHaveBeenCalledWith('district-1')
  })

  it('removes request after decision', async () => {
    const store = useInvitationsStore()
    store.items = [
      {
        id: 'req-1',
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
      },
    ]

    await store.decide('req-1', 'ACCEPTED')
    expect(store.items).toHaveLength(0)
  })
})
