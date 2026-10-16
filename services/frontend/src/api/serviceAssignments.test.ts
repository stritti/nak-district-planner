// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./client')

import * as client from './client'
import { changeAssignmentInline, createAssignment, deleteAssignment, updateAssignment } from './serviceAssignments'

const apiFetch = vi.mocked(client.apiFetch)

describe('service assignment API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiFetch.mockResolvedValue({})
  })

  it('normalizes optional leader values and uses ASSIGNED by default', async () => {
    await createAssignment('event-1', {}, '"rev-1"')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/events/event-1/assignments', {
      method: 'POST',
      headers: { 'If-Match': '"rev-1"' },
      body: JSON.stringify({ leader_id: null, leader_name: null, status: 'ASSIGNED' }),
    })
  })

  it('includes explicit status and warning confirmation when provided', async () => {
    await createAssignment(
      'event-1',
      { leaderId: 'leader-1', leaderName: 'Pr. Beispiel', confirmWarnings: false },
      '"rev-1"',
      'CONFIRMED',
    )
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/events/event-1/assignments', {
      method: 'POST',
      headers: { 'If-Match': '"rev-1"' },
      body: JSON.stringify({
        leader_id: 'leader-1',
        leader_name: 'Pr. Beispiel',
        status: 'CONFIRMED',
        confirm_warnings: false,
      }),
    })
  })

  it('updates only explicitly supplied optional fields', async () => {
    await updateAssignment('event-1', 'assignment-1', { leaderName: 'Gast' }, '"rev-1"')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/events/event-1/assignments/assignment-1', {
      method: 'PUT',
      headers: { 'If-Match': '"rev-1"' },
      body: JSON.stringify({ leader_id: null, leader_name: 'Gast' }),
    })

    await updateAssignment(
      'event-1',
      'assignment-1',
      { leaderId: 'leader-1', confirmWarnings: true },
      '"rev-2"',
      'OPEN',
    )
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/events/event-1/assignments/assignment-1', {
      method: 'PUT',
      headers: { 'If-Match': '"rev-2"' },
      body: JSON.stringify({
        leader_id: 'leader-1',
        leader_name: null,
        status: 'OPEN',
        confirm_warnings: true,
      }),
    })
  })

  it('sends a conditional inline mutation and an explicit warning acknowledgment', async () => {
    await changeAssignmentInline('event-1', 'leader-1', '"rev-1"', true)
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/events/event-1/assignments/inline', {
      method: 'PUT',
      headers: { 'If-Match': '"rev-1"' },
      body: JSON.stringify({ leader_id: 'leader-1', confirm_warnings: true }),
    })
  })

  it('never sends an inline assignment without revision or selected leader', async () => {
    await expect(changeAssignmentInline('e', 'l', '')).rejects.toThrow('Versionsinformation')
    await expect(changeAssignmentInline('e', '', '"rev"')).rejects.toThrow('Person erforderlich')
    expect(apiFetch).not.toHaveBeenCalled()
  })

  it('deletes an assignment', async () => {
    await deleteAssignment('event-1', 'assignment-1', '"rev-1"')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/events/event-1/assignments/assignment-1', {
      method: 'DELETE',
      headers: { 'If-Match': '"rev-1"' },
    })
  })

  it('never sends a dialog write without a revision (no blind create, update or delete)', async () => {
    await expect(createAssignment('e', {}, '')).rejects.toThrow('Versionsinformation')
    await expect(updateAssignment('e', 'a', {}, '')).rejects.toThrow('Versionsinformation')
    await expect(deleteAssignment('e', 'a', '')).rejects.toThrow('Versionsinformation')
    expect(apiFetch).not.toHaveBeenCalled()
  })
})
