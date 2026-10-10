// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./client')

import * as client from './client'
import { createExportToken, deleteExportToken, listExportTokens } from './exportTokens'

const apiFetch = vi.mocked(client.apiFetch)

describe('export token API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiFetch.mockResolvedValue({})
  })

  it('lists all tokens or filters by district', async () => {
    await listExportTokens()
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/export-tokens')

    await listExportTokens('district-1')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/export-tokens?district_id=district-1')
  })

  it('creates and deletes tokens', async () => {
    const payload = {
      label: 'Kalender',
      token_type: 'PUBLIC' as const,
      district_id: 'district-1',
      congregation_id: null,
    }
    await createExportToken(payload)
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/export-tokens', {
      method: 'POST',
      body: JSON.stringify(payload),
    })

    await deleteExportToken('token-1')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/export-tokens/token-1', {
      method: 'DELETE',
    })
  })
})
