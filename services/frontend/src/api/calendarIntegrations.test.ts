import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./client')

import * as client from './client'
import {
  createIntegration,
  deleteIntegration,
  listIntegrations,
  triggerSync,
  updateIntegration,
} from './calendarIntegrations'

const apiFetch = vi.mocked(client.apiFetch)

describe('calendar integrations API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiFetch.mockResolvedValue({})
  })

  it('lists all integrations or filters by district', async () => {
    await listIntegrations()
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/calendar-integrations')

    await listIntegrations('district-1')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/calendar-integrations?district_id=district-1')
  })

  it('creates an integration with its full provider configuration', async () => {
    const payload = {
      district_id: 'district-1',
      congregation_id: null,
      name: 'Gemeindekalender',
      type: 'ICS' as const,
      credentials: { url: 'https://calendar.example/feed.ics' },
      sync_interval: 60,
      capabilities: ['READ'] as const,
      default_category: 'Gottesdienst',
    }

    await createIntegration({ ...payload, capabilities: [...payload.capabilities] })

    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/calendar-integrations', {
      method: 'POST',
      body: JSON.stringify({ ...payload, capabilities: ['READ'] }),
    })
  })

  it('updates, synchronizes and deletes an integration', async () => {
    await updateIntegration('integration-1', {
      name: 'Neu',
      sync_interval: 15,
      capabilities: ['READ', 'WRITE'],
    })
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/calendar-integrations/integration-1', {
      method: 'PATCH',
      body: JSON.stringify({
        name: 'Neu',
        sync_interval: 15,
        capabilities: ['READ', 'WRITE'],
      }),
    })

    await triggerSync('integration-1')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/calendar-integrations/integration-1/sync', {
      method: 'POST',
    })

    await deleteIntegration('integration-1')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/calendar-integrations/integration-1', {
      method: 'DELETE',
    })
  })
})
