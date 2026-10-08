import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./client')

import * as client from './client'
import { createAssignment, deleteAssignment, updateAssignment } from './serviceAssignments'

const apiFetch = vi.mocked(client.apiFetch)

describe('service assignment API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiFetch.mockResolvedValue({})
  })

  it('normalizes optional leader values and uses ASSIGNED by default', async () => {
    await createAssignment('event-1', {})
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/events/event-1/assignments', {
      method: 'POST',
      body: JSON.stringify({ leader_id: null, leader_name: null, status: 'ASSIGNED' }),
    })
  })

  it('includes explicit status and warning confirmation when provided', async () => {
    await createAssignment(
      'event-1',
      { leaderId: 'leader-1', leaderName: 'Pr. Beispiel', confirmWarnings: false },
      'CONFIRMED',
    )
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/events/event-1/assignments', {
      method: 'POST',
      body: JSON.stringify({
        leader_id: 'leader-1',
        leader_name: 'Pr. Beispiel',
        status: 'CONFIRMED',
        confirm_warnings: false,
      }),
    })
  })

  it('updates only explicitly supplied optional fields', async () => {
    await updateAssignment('event-1', 'assignment-1', { leaderName: 'Gast' })
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/events/event-1/assignments/assignment-1', {
      method: 'PUT',
      body: JSON.stringify({ leader_id: null, leader_name: 'Gast' }),
    })

    await updateAssignment(
      'event-1',
      'assignment-1',
      { leaderId: 'leader-1', confirmWarnings: true },
      'OPEN',
    )
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/events/event-1/assignments/assignment-1', {
      method: 'PUT',
      body: JSON.stringify({
        leader_id: 'leader-1',
        leader_name: null,
        status: 'OPEN',
        confirm_warnings: true,
      }),
    })
  })

  it('deletes an assignment', async () => {
    await deleteAssignment('event-1', 'assignment-1')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/events/event-1/assignments/assignment-1', {
      method: 'DELETE',
    })
  })
})
