// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./client')

import * as client from './client'
import {
  acceptExternalCandidate,
  dismissExternalCandidate,
  listExternalCandidates,
} from './externalCandidates'

describe('external candidates API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(client.apiFetch).mockResolvedValue([])
  })

  it('lists pending candidates for the selected district', async () => {
    await listExternalCandidates('district 1')

    expect(client.apiFetch).toHaveBeenCalledWith(
      '/api/v1/external-candidates?district_id=district+1&status=PENDING',
    )
  })

  it('supports an explicit candidate status', async () => {
    await listExternalCandidates('district-1', 'DISMISSED')

    expect(client.apiFetch).toHaveBeenCalledWith(
      '/api/v1/external-candidates?district_id=district-1&status=DISMISSED',
    )
  })

  it('accepts a candidate by creating a new planning slot', async () => {
    await acceptExternalCandidate('candidate-1')

    expect(client.apiFetch).toHaveBeenCalledWith('/api/v1/external-candidates/candidate-1/accept', {
      method: 'POST',
      body: JSON.stringify({ matched_slot_id: null }),
    })
  })

  it('passes an existing planning slot when supplied', async () => {
    await acceptExternalCandidate('candidate-1', 'slot-1')

    expect(client.apiFetch).toHaveBeenCalledWith('/api/v1/external-candidates/candidate-1/accept', {
      method: 'POST',
      body: JSON.stringify({ matched_slot_id: 'slot-1' }),
    })
  })

  it('dismisses a candidate', async () => {
    await dismissExternalCandidate('candidate-1')

    expect(client.apiFetch).toHaveBeenCalledWith('/api/v1/external-candidates/candidate-1/dismiss', {
      method: 'POST',
    })
  })
})
