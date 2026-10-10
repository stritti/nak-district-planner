// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./client')

import * as client from './client'
import {
  bulkUpdateApprovalStatus,
  listEvents,
  resolveEventConflict,
  updateEvent,
} from './events'

describe('events api', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(client.apiFetch).mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 })
  })

  it('calls /api/v1/events without params when none given', async () => {
    await listEvents()
    expect(client.apiFetch).toHaveBeenCalledWith('/api/v1/events')
  })

  it('serializes every supported list filter', async () => {
    await listEvents({
      district_id: 'district 1',
      congregation_id: 'congregation-1',
      group_id: 'group-1',
      only_district_level: true,
      status: 'ACTIVE',
      approval_status: 'CONFIRMED',
      is_service: false,
      from_dt: '2026-03-01T00:00:00Z',
      to_dt: '2026-03-31T23:59:59Z',
      limit: 0,
      offset: 0,
    })

    const url = vi.mocked(client.apiFetch).mock.calls[0][0] as string
    const query = new URL(url, 'https://example.test').searchParams
    expect(query.get('district_id')).toBe('district 1')
    expect(query.get('congregation_id')).toBe('congregation-1')
    expect(query.get('group_id')).toBe('group-1')
    expect(query.get('only_district_level')).toBe('true')
    expect(query.get('status')).toBe('ACTIVE')
    expect(query.get('approval_status')).toBe('CONFIRMED')
    expect(query.get('is_service')).toBe('false')
    expect(query.get('from_dt')).toBe('2026-03-01T00:00:00Z')
    expect(query.get('to_dt')).toBe('2026-03-31T23:59:59Z')
    expect(query.get('limit')).toBe('0')
    expect(query.get('offset')).toBe('0')
  })

  it('omits false-only and undefined list filters', async () => {
    await listEvents({ only_district_level: false, congregation_id: undefined })
    expect(client.apiFetch).toHaveBeenCalledWith('/api/v1/events')
  })

  it('sends PATCH to /api/v1/events/:id with body', async () => {
    vi.mocked(client.apiFetch).mockResolvedValue({ id: '1' })
    await updateEvent('1', { status: 'ACTIVE' })
    expect(client.apiFetch).toHaveBeenCalledWith('/api/v1/events/1', {
      method: 'PATCH',
      body: JSON.stringify({ status: 'ACTIVE' }),
    })
  })

  it('resolves an event conflict through its dedicated action', async () => {
    await resolveEventConflict('event-1')
    expect(client.apiFetch).toHaveBeenCalledWith('/api/v1/events/event-1/resolve-conflict', {
      method: 'POST',
    })
  })

  it('bulk-updates approval status for a district', async () => {
    const payload = { year: 2026, month: 10, approval_status: 'CONFIRMED' as const }
    await bulkUpdateApprovalStatus('district-1', payload)

    expect(client.apiFetch).toHaveBeenCalledWith(
      '/api/v1/events/bulk-approval-status?district_id=district-1',
      { method: 'POST', body: JSON.stringify(payload) },
    )
  })

  it('bulk-updates approval status without an empty district query', async () => {
    const payload = { year: 2026, month: 10, approval_status: 'PLANNED' as const }
    await bulkUpdateApprovalStatus('', payload)

    expect(client.apiFetch).toHaveBeenCalledWith('/api/v1/events/bulk-approval-status', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  })
})
