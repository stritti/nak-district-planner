// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import * as calendarApi from '../api/calendarIntegrations'
import { useCalendarIntegrationsStore } from './calendarIntegrations'

vi.mock('../api/calendarIntegrations')

const integration = (overrides: Partial<calendarApi.CalendarIntegrationResponse> = {}): calendarApi.CalendarIntegrationResponse => ({
  id: 'integration-1',
  district_id: 'district-1',
  congregation_id: null,
  name: 'Calendar',
  type: 'ICS',
  sync_interval: 60,
  capabilities: ['READ'],
  is_active: true,
  last_synced_at: null,
  last_sync_error: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  default_category: null,
  ...overrides,
})
const syncResult: calendarApi.SyncResult = {
  integration_id: 'integration-1',
  created: 1,
  updated: 2,
  cancelled: 0,
  auto_matched: 1,
}

describe('useCalendarIntegrationsStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  it('loads integrations, remembers the filter and clears a previous load error', async () => {
    vi.mocked(calendarApi.listIntegrations).mockResolvedValue({ items: [integration()], total: 1 })
    const store = useCalendarIntegrationsStore()
    store.error = 'old error'

    await store.fetchIntegrations('district-1')

    expect(calendarApi.listIntegrations).toHaveBeenCalledWith('district-1')
    expect(store.integrations).toEqual([integration()])
    expect(store.districtFilter).toBe('district-1')
    expect(store.error).toBeNull()
    expect(store.loading).toBe(false)
  })

  it('exposes Error and non-Error load failures without leaving loading active', async () => {
    const store = useCalendarIntegrationsStore()
    vi.mocked(calendarApi.listIntegrations).mockRejectedValueOnce(new Error('load failed'))
    await store.fetchIntegrations()
    expect(store.error).toBe('load failed')
    expect(store.loading).toBe(false)

    vi.mocked(calendarApi.listIntegrations).mockRejectedValueOnce('unknown')
    await store.fetchIntegrations()
    expect(store.error).toBe('Fehler beim Laden')
  })

  it('owns create, update and delete collection transitions', async () => {
    const store = useCalendarIntegrationsStore()
    const existing = integration()
    const created = integration({ id: 'created', name: 'Created' })
    const updated = integration({ name: 'Updated' })
    store.integrations = [existing]
    vi.mocked(calendarApi.createIntegration).mockResolvedValue(created)
    vi.mocked(calendarApi.updateIntegration).mockResolvedValue(updated)
    vi.mocked(calendarApi.deleteIntegration).mockResolvedValue(undefined)

    const createPayload: calendarApi.CalendarIntegrationCreate = {
      district_id: 'district-1',
      name: 'Created',
      type: 'ICS',
      credentials: { url: 'https://example.org/feed.ics' },
      sync_interval: 60,
      capabilities: ['READ'],
    }
    await expect(store.create(createPayload)).resolves.toEqual(created)
    expect(store.integrations[0]).toEqual(created)

    const updatePayload: calendarApi.CalendarIntegrationUpdate = { name: 'Updated' }
    await expect(store.update('integration-1', updatePayload)).resolves.toEqual(updated)
    expect(store.integrations.find((item) => item.id === 'integration-1')?.name).toBe('Updated')

    await store.remove('created')
    expect(calendarApi.deleteIntegration).toHaveBeenCalledWith('created')
    expect(store.integrations.some((item) => item.id === 'created')).toBe(false)
  })

  it('returns updates for an item no longer in the current collection without inserting it', async () => {
    const store = useCalendarIntegrationsStore()
    const updated = integration({ id: 'other', name: 'Other' })
    vi.mocked(calendarApi.updateIntegration).mockResolvedValue(updated)

    await expect(store.update('other', { name: 'Other' })).resolves.toEqual(updated)
    expect(store.integrations).toEqual([])
  })

  it('stores a successful sync result, preserves the district filter and clears stale errors', async () => {
    vi.mocked(calendarApi.triggerSync).mockResolvedValue(syncResult)
    vi.mocked(calendarApi.listIntegrations).mockResolvedValue({ items: [integration()], total: 1 })
    const store = useCalendarIntegrationsStore()
    await store.fetchIntegrations('district-1')
    vi.mocked(calendarApi.listIntegrations).mockClear()
    store.syncErrors['integration-1'] = 'old sync error'

    await expect(store.triggerIntegrationSync('integration-1')).resolves.toEqual(syncResult)

    expect(store.syncResults['integration-1']).toEqual(syncResult)
    expect(store.syncErrors['integration-1']).toBeUndefined()
    expect(calendarApi.listIntegrations).toHaveBeenCalledWith('district-1')
    expect(store.syncingId).toBeNull()
  })

  it('records sync failures and supports explicitly clearing them', async () => {
    const store = useCalendarIntegrationsStore()
    vi.mocked(calendarApi.triggerSync).mockRejectedValueOnce(new Error('provider down'))

    await expect(store.triggerIntegrationSync('integration-1')).resolves.toBeNull()
    expect(store.syncErrors['integration-1']).toBe('provider down')
    expect(store.syncingId).toBeNull()

    store.clearSyncError('integration-1')
    expect(store.syncErrors['integration-1']).toBeUndefined()

    vi.mocked(calendarApi.triggerSync).mockRejectedValueOnce('unknown')
    await store.triggerIntegrationSync('integration-1')
    expect(store.syncErrors['integration-1']).toBe('Sync fehlgeschlagen')
  })
})
