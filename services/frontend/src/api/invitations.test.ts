import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./client')

import * as client from './client'
import {
  createInvitations,
  decideOverwriteRequest,
  deleteInvitation,
  listEventInvitations,
  listOverwriteRequests,
} from './invitations'

describe('invitations api', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(client.apiFetch).mockResolvedValue([])
  })

  it('creates invitation targets for an event', async () => {
    const targets = [
      { target_type: 'DISTRICT_CONGREGATION' as const, target_congregation_id: 'c1' },
      { target_type: 'EXTERNAL_NOTE' as const, external_target_note: 'Nachbarbezirk' },
    ]

    await createInvitations('event-1', targets)

    expect(client.apiFetch).toHaveBeenCalledWith('/api/v1/events/event-1/invitations', {
      method: 'POST',
      body: JSON.stringify({ targets }),
    })
  })

  it('lists invitations for one event', async () => {
    await listEventInvitations('event-1')
    expect(client.apiFetch).toHaveBeenCalledWith('/api/v1/events/event-1/invitations')
  })

  it('deletes one invitation', async () => {
    await deleteInvitation('invitation-1')
    expect(client.apiFetch).toHaveBeenCalledWith('/api/v1/invitations/invitation-1', {
      method: 'DELETE',
    })
  })

  it('loads overwrite requests by district and URL-encodes the id', async () => {
    await listOverwriteRequests('district 1')
    expect(client.apiFetch).toHaveBeenCalledWith(
      '/api/v1/invitations/overwrite-requests?district_id=district+1',
    )
  })

  it.each(['ACCEPTED', 'REJECTED'] as const)(
    'sends %s decision payload for overwrite request',
    async (decision) => {
      await decideOverwriteRequest('req-1', decision)
      expect(client.apiFetch).toHaveBeenCalledWith(
        '/api/v1/invitations/overwrite-requests/req-1/decision',
        {
          method: 'POST',
          body: JSON.stringify({ decision }),
        },
      )
    },
  )
})
