import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createLeaderUnavailability, listLeaderUnavailabilities } from './leaderUnavailabilities'

const apiFetchMock = vi.fn()

vi.mock('./client', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}))

describe('leader unavailability API', () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue([])
  })

  it('lists unavailabilities scoped to a district and leader', async () => {
    await listLeaderUnavailabilities('district-1', 'leader-1')

    expect(apiFetchMock).toHaveBeenCalledWith(
      '/api/v1/districts/district-1/leader-unavailabilities?leader_id=leader-1',
    )
  })

  it('creates an unavailability with the API contract', async () => {
    await createLeaderUnavailability('district-1', {
      leader_id: 'leader-1',
      start_at: '2026-09-17T10:00:00.000Z',
      end_at: '2026-09-17T12:00:00.000Z',
      reason: 'URLAUB',
      note: 'Familientermin',
    })

    expect(apiFetchMock).toHaveBeenCalledWith(
      '/api/v1/districts/district-1/leader-unavailabilities',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          leader_id: 'leader-1',
          start_at: '2026-09-17T10:00:00.000Z',
          end_at: '2026-09-17T12:00:00.000Z',
          reason: 'URLAUB',
          note: 'Familientermin',
        }),
      }),
    )
  })
})
