import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import * as calendarApi from '../api/calendarIntegrations'
import { useCalendarIntegrationsStore } from './calendarIntegrations'

vi.mock('../api/calendarIntegrations')

const integration = { id: 'integration-1', name: 'Calendar' } as calendarApi.CalendarIntegrationResponse
const syncResult = {
  created: 1,
  updated: 2,
  cancelled: 0,
  auto_matched: 1,
} as calendarApi.SyncResult

describe('useCalendarIntegrationsStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  it('loads integrations and clears a previous load error', async () => {
    vi.mocked(calendarApi.listIntegrations).mockResolvedValue({ items: [integration], total: 1 })
    const store = useCalendarIntegrationsStore()
    store.error = 'old error'

    await store.fetchIntegrations('district-1')

    expect(calendarApi.listIntegrations).toHaveBeenCalledWith('district-1')
    expect(store.integrations).toEqual([integration])
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

  it('stores a successful sync result, refreshes integrations and clears stale errors', async () => {
    vi.mocked(calendarApi.triggerSync).mockResolvedValue(syncResult)
    vi.mocked(calendarApi.listIntegrations).mockResolvedValue({ items: [integration], total: 1 })
    const store = useCalendarIntegrationsStore()
    store.syncErrors[integration.id] = 'old sync error'

    await expect(store.triggerIntegrationSync(integration.id)).resolves.toEqual(syncResult)

    expect(store.syncResults[integration.id]).toEqual(syncResult)
    expect(store.syncErrors[integration.id]).toBeUndefined()
    expect(calendarApi.listIntegrations).toHaveBeenCalledWith(undefined)
    expect(store.syncingId).toBeNull()
  })

  it('records sync failures and supports explicitly clearing them', async () => {
    const store = useCalendarIntegrationsStore()
    vi.mocked(calendarApi.triggerSync).mockRejectedValueOnce(new Error('provider down'))

    await expect(store.triggerIntegrationSync(integration.id)).resolves.toBeNull()
    expect(store.syncErrors[integration.id]).toBe('provider down')
    expect(store.syncingId).toBeNull()

    store.clearSyncError(integration.id)
    expect(store.syncErrors[integration.id]).toBeUndefined()

    vi.mocked(calendarApi.triggerSync).mockRejectedValueOnce('unknown')
    await store.triggerIntegrationSync(integration.id)
    expect(store.syncErrors[integration.id]).toBe('Sync fehlgeschlagen')
  })
})
