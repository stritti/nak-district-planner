import { describe, it, expect, vi, beforeEach } from 'vitest'
import { listEvents, updateEvent } from './events'
import * as client from './client'

vi.mock('./client')

describe('listEvents', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(client.apiFetch).mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 })
  })

  it('calls /api/v1/events without params when none given', async () => {
    await listEvents()
    expect(client.apiFetch).toHaveBeenCalledWith('/api/v1/events')
  })

  it('appends district_id to query string', async () => {
    await listEvents({ district_id: 'abc' })
    expect(client.apiFetch).toHaveBeenCalledWith('/api/v1/events?district_id=abc')
  })

  it('appends multiple query params', async () => {
    await listEvents({ district_id: 'abc', status: 'PUBLISHED', limit: 10, offset: 20 })
    const url = vi.mocked(client.apiFetch).mock.calls[0][0] as string
    expect(url).toContain('district_id=abc')
    expect(url).toContain('status=PUBLISHED')
    expect(url).toContain('limit=10')
    expect(url).toContain('offset=20')
  })

  it('omits undefined params', async () => {
    await listEvents({ congregation_id: undefined, limit: 5 })
    const url = vi.mocked(client.apiFetch).mock.calls[0][0] as string
    expect(url).not.toContain('congregation_id')
    expect(url).toContain('limit=5')
  })

  it('appends date range params', async () => {
    await listEvents({ from_dt: '2026-03-01', to_dt: '2026-03-31' })
    const url = vi.mocked(client.apiFetch).mock.calls[0][0] as string
    expect(url).toContain('from_dt=2026-03-01')
    expect(url).toContain('to_dt=2026-03-31')
  })
})

describe('updateEvent', () => {
  it('sends PATCH to /api/v1/events/:id with body', async () => {
    vi.mocked(client.apiFetch).mockResolvedValue({ id: '1' })
    await updateEvent('1', { status: 'PUBLISHED' })
    expect(client.apiFetch).toHaveBeenCalledWith('/api/v1/events/1', {
      method: 'PATCH',
      body: JSON.stringify({ status: 'PUBLISHED' }),
    })
  })
})
