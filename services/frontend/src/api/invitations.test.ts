import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./client')

import * as client from './client'
import { decideOverwriteRequest, listOverwriteRequests } from './invitations'

describe('invitations api', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(client.apiFetch).mockResolvedValue([])
  })

  it('loads overwrite requests by district', async () => {
    await listOverwriteRequests('district-1')
    expect(client.apiFetch).toHaveBeenCalledWith(
      '/api/v1/invitations/overwrite-requests?district_id=district-1',
    )
  })

  it('sends decision payload for overwrite request', async () => {
    await decideOverwriteRequest('req-1', 'ACCEPTED')
    expect(client.apiFetch).toHaveBeenCalledWith(
      '/api/v1/invitations/overwrite-requests/req-1/decision',
      {
        method: 'POST',
        body: JSON.stringify({ decision: 'ACCEPTED' }),
      },
    )
  })
})
