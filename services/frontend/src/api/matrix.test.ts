import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./client')

import * as client from './client'
import { fetchMatrix } from './matrix'

const apiFetch = vi.mocked(client.apiFetch)

describe('matrix API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiFetch.mockResolvedValue({ dates: [], rows: [], holidays: {} })
  })

  it('serializes the required date range', async () => {
    await fetchMatrix('district-1', '2027-01-01', '2027-01-31')
    const [url] = apiFetch.mock.calls[0]
    expect(url).toContain('/api/v1/districts/district-1/matrix?')
    expect(url).toContain('from_dt=2027-01-01')
    expect(url).toContain('to_dt=2027-01-31')
    expect(url).not.toContain('group_id=')
  })

  it('adds a group filter only when provided', async () => {
    await fetchMatrix('district-1', '2027-01-01', '2027-01-31', 'group-1')
    expect(apiFetch.mock.calls[0][0]).toContain('group_id=group-1')
  })
})
