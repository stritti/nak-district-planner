// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from './recurringEvents'
import { apiFetch } from './client'

vi.mock('./client', () => ({ apiFetch: vi.fn() }))

const templatesUrl = '/api/v1/districts/district%2Fa/recurring-event-templates'
const checklistUrl = '/api/v1/districts/district%2Fa/recurring-event-checklist'

const recurrence: api.RecurrenceRule = {
  kind: 'WEEKLY',
  anchor_date: '2026-11-03',
  interval: 1,
  weekdays: [2],
  day_of_month: null,
  weekday: null,
  ordinal: null,
  version: 1,
}

const template: api.RecurringTemplateInput = {
  title: 'Chorprobe',
  description: null,
  category: 'Musik',
  congregation_id: null,
  start_time: '19:30',
  duration_minutes: 90,
  recurrence,
  applicability: ['all'],
  excluded_dates: ['2026-11-17'],
  active_from: null,
  active_until: null,
  is_active: true,
}

const action: api.OccurrenceAccept = {
  template_id: 't',
  occurrence_local_date: '2026-11-03',
  template_revision: 4,
}

beforeEach(() => {
  vi.resetAllMocks()
})

describe('recurring events API', () => {
  it('loads the district templates with an encoded identifier', async () => {
    await api.listRecurringTemplates('district/a')
    expect(apiFetch).toHaveBeenCalledWith(`${templatesUrl}?limit=50&offset=0`)
  })

  it('uses requested limits and offsets for the template list', async () => {
    await api.listRecurringTemplates('district/a', 20, 40)
    expect(apiFetch).toHaveBeenCalledWith(`${templatesUrl}?limit=20&offset=40`)
  })

  it('creates and updates templates without dropping recurrence metadata', async () => {
    await api.createRecurringTemplate('district/a', template)
    expect(apiFetch).toHaveBeenNthCalledWith(1, templatesUrl, {
      method: 'POST', body: JSON.stringify(template),
    })
    await api.updateRecurringTemplate('district/a', 'template/2', {
      recurrence, expected_revision: 2, is_active: false,
    })
    expect(apiFetch).toHaveBeenNthCalledWith(2, `${templatesUrl}/template%2F2`, {
      method: 'PATCH',
      body: JSON.stringify({ recurrence, expected_revision: 2, is_active: false }),
    })
  })

  it('always sends the month and pagination defaults', async () => {
    await api.listRecurringChecklist('district/a', { year: 2026, month: 11 })
    const [url] = vi.mocked(apiFetch).mock.calls[0]
    expect(url).toBe(`${checklistUrl}?year=2026&month=11&limit=50&offset=0`)
  })

  it('includes all optional server-side filters when provided', async () => {
    await api.listRecurringChecklist('district/a', {
      year: 2026,
      month: 12,
      congregation_id: 'c',
      q: 'Chor&Gesang',
      category: 'Musik',
      status: 'SKIPPED',
      limit: 7,
      offset: 14,
    })
    const [url] = vi.mocked(apiFetch).mock.calls[0]
    const query = new URL(String(url), 'http://localhost').searchParams
    expect(query.get('congregation_id')).toBe('c')
    expect(query.get('q')).toBe('Chor&Gesang')
    expect(query.get('category')).toBe('Musik')
    expect(query.get('status')).toBe('SKIPPED')
    expect(query.get('limit')).toBe('7')
    expect(query.get('offset')).toBe('14')
  })

  it('posts individual accept, skip and reopen requests', async () => {
    await api.acceptRecurringOccurrence('district/a', action)
    await api.skipRecurringOccurrence('district/a', action)
    await api.reopenRecurringOccurrence('district/a', action)
    for (const [index, name] of ['accept', 'skip', 'reopen'].entries()) {
      expect(apiFetch).toHaveBeenNthCalledWith(index + 1, `${checklistUrl}/${name}`, {
        method: 'POST', body: JSON.stringify(action),
      })
    }
  })

  it('posts explicit missing-slot resolution with the selected slot', async () => {
    const body: api.ResolveRequest = { ...action, action: 'LINK_EXISTING', planning_slot_id: 'slot' }
    await api.resolveRecurringOccurrence('district/a', body)
    expect(apiFetch).toHaveBeenCalledWith(`${checklistUrl}/resolve`, {
      method: 'POST', body: JSON.stringify(body),
    })
  })

  it('submits bulk-selected occurrences atomically per item', async () => {
    await api.bulkAcceptRecurringOccurrences('district/a', [action, action])
    expect(apiFetch).toHaveBeenCalledWith(`${checklistUrl}/bulk-accept`, {
      method: 'POST', body: JSON.stringify({ items: [action, action] }),
    })
  })

  it('forwards backend rejections without silently marking an item successful', async () => {
    const rejected = new Error('409 revision conflict')
    vi.mocked(apiFetch).mockRejectedValueOnce(rejected)
    await expect(api.acceptRecurringOccurrence('district/a', action)).rejects.toBe(rejected)
  })
})
