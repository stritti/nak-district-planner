// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { vi } from 'vitest'

vi.mock('./client')

import { describe, it, expect, beforeEach } from 'vitest'
import {
  createUnavailability,
  deleteUnavailability,
  listUnavailabilities,
  planningDayBounds,
  unavailabilityReasonLabel,
  type UnavailabilityReason,
} from './leaderUnavailabilities'
import * as client from './client'

describe('leaderUnavailabilities API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('lists all unavailabilities without leader filter', async () => {
    vi.mocked(client.apiFetch).mockResolvedValue([])
    await listUnavailabilities('district-1')
    expect(client.apiFetch).toHaveBeenCalledWith(
      '/api/v1/districts/district-1/leader-unavailabilities',
    )
  })

  it('appends leader_id query param when given', async () => {
    vi.mocked(client.apiFetch).mockResolvedValue([])
    await listUnavailabilities('district-1', 'leader-1')
    expect(client.apiFetch).toHaveBeenCalledWith(
      '/api/v1/districts/district-1/leader-unavailabilities?leader_id=leader-1',
    )
  })

  it('creates an unavailability via POST', async () => {
    const created = {
      id: 'unavail-1',
      leader_id: 'leader-1',
      start_at: '2026-05-01T00:00:00.000Z',
      end_at: '2026-05-03T00:00:00.000Z',
      reason: 'URLAUB' as const,
      note: null,
      created_at: '2026-04-01T00:00:00.000Z',
      updated_at: '2026-04-01T00:00:00.000Z',
    }
    vi.mocked(client.apiFetch).mockResolvedValue(created)
    const result = await createUnavailability('district-1', {
      leader_id: 'leader-1',
      start_at: '2026-05-01T00:00:00.000Z',
      end_at: '2026-05-03T00:00:00.000Z',
      reason: 'URLAUB',
    })
    expect(result).toEqual(created)
    expect(client.apiFetch).toHaveBeenCalledWith(
      '/api/v1/districts/district-1/leader-unavailabilities',
      {
        method: 'POST',
        body: JSON.stringify({
          leader_id: 'leader-1',
          start_at: '2026-05-01T00:00:00.000Z',
          end_at: '2026-05-03T00:00:00.000Z',
          reason: 'URLAUB',
        }),
      },
    )
  })

  it('deletes an unavailability via DELETE', async () => {
    vi.mocked(client.apiFetch).mockResolvedValue(undefined)
    await deleteUnavailability('district-1', 'unavail-1')
    expect(client.apiFetch).toHaveBeenCalledWith(
      '/api/v1/districts/district-1/leader-unavailabilities/unavail-1',
      { method: 'DELETE' },
    )
  })

  it('builds Europe/Berlin day bounds independent of browser timezone', () => {
    expect(planningDayBounds('2026-05-01')).toEqual({
      start: '2026-04-30T22:00:00.000Z',
      end: '2026-05-01T21:59:59.999Z',
    })
  })

  it('handles DST transition days correctly', () => {
    expect(planningDayBounds('2026-03-29')).toEqual({
      start: '2026-03-28T23:00:00.000Z',
      end: '2026-03-29T21:59:59.999Z',
    })
    expect(planningDayBounds('2026-10-25')).toEqual({
      start: '2026-10-24T22:00:00.000Z',
      end: '2026-10-25T22:59:59.999Z',
    })
  })

  it('maps reason values to German labels', () => {
    expect(unavailabilityReasonLabel('URLAUB')).toBe('Urlaub')
    expect(unavailabilityReasonLabel('SPERRZEIT')).toBe('Sperrzeit')
    expect(unavailabilityReasonLabel('FORTBILDUNG')).toBe('Fortbildung')
    expect(unavailabilityReasonLabel('SONSTIGES')).toBe('Sonstiges')
    expect(unavailabilityReasonLabel('UNKNOWN' as UnavailabilityReason)).toBe('UNKNOWN')
  })
})
