import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createAssignment, updateAssignment } from './serviceAssignments'

const apiFetchMock = vi.fn()

vi.mock('./client', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}))

describe('service assignment API', () => {
  beforeEach(() => {
    apiFetchMock.mockResolvedValue({ id: 'assignment-1' })
  })

  it('sends warning confirmation when creating an assignment', async () => {
    await createAssignment('event-1', { leaderId: 'leader-1' }, 'ASSIGNED', true)

    expect(apiFetchMock).toHaveBeenCalledWith(
      '/api/v1/events/event-1/assignments',
      expect.objectContaining({
        body: JSON.stringify({
          leader_id: 'leader-1',
          leader_name: null,
          status: 'ASSIGNED',
          confirm_warnings: true,
        }),
      }),
    )
  })

  it('sends warning confirmation when updating an assignment', async () => {
    await updateAssignment('event-1', 'assignment-1', { leaderId: 'leader-1' }, undefined, true)

    expect(apiFetchMock).toHaveBeenCalledWith(
      '/api/v1/events/event-1/assignments/assignment-1',
      expect.objectContaining({
        body: JSON.stringify({
          leader_id: 'leader-1',
          leader_name: null,
          confirm_warnings: true,
        }),
      }),
    )
  })
})