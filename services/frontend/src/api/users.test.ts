// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./client')

import * as client from './client'
import { assignMembership, listUsers, removeMembership, setSuperadmin } from './users'

const apiFetch = vi.mocked(client.apiFetch)

describe('users API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiFetch.mockResolvedValue({})
  })

  it('calls the user administration endpoints and encodes the subject', async () => {
    await listUsers()
    await assignMembership('auth0|a/b', { scope_type: 'DISTRICT', scope_id: 'd1', role: 'PLANNER' })
    await removeMembership('auth0|a/b', 'm1')
    await setSuperadmin('auth0|a/b', true)

    expect(apiFetch.mock.calls).toEqual([
      ['/api/v1/users'],
      [
        '/api/v1/users/auth0%7Ca%2Fb/memberships',
        { method: 'PUT', body: JSON.stringify({ scope_type: 'DISTRICT', scope_id: 'd1', role: 'PLANNER' }) },
      ],
      ['/api/v1/users/auth0%7Ca%2Fb/memberships/m1', { method: 'DELETE' }],
      ['/api/v1/users/auth0%7Ca%2Fb/superadmin', { method: 'PUT', body: JSON.stringify({ is_superadmin: true }) }],
    ])
  })
})
