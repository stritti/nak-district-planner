import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useEventsStore } from './events'
import * as eventsApi from '../api/events'

vi.mock('../api/events')

const makeListResponse = (
  items: Partial<eventsApi.EventResponse>[] = [],
  total = 0,
): eventsApi.EventListResponse => ({
  items: items as eventsApi.EventResponse[],
  total,
  limit: 50,
  offset: 0,
})

describe('useEventsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(eventsApi.listEvents).mockResolvedValue(makeListResponse())
  })

  it('initialises with empty state', () => {
    const store = useEventsStore()
    expect(store.items).toEqual([])
    expect(store.total).toBe(0)
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it('currentPage starts at 1', () => {
    const store = useEventsStore()
    expect(store.currentPage).toBe(1)
  })

  it('totalPages is 0 when total is 0', () => {
    const store = useEventsStore()
    expect(store.totalPages).toBe(0)
  })

  it('totalPages rounds up to next page', async () => {
    vi.mocked(eventsApi.listEvents).mockResolvedValue(makeListResponse([], 51))
    const store = useEventsStore()
    await store.fetch()
    expect(store.totalPages).toBe(2)
  })

  it('fetch sets items and total from API response', async () => {
    const items = [{ id: '1', title: 'Gottesdienst' }]
    vi.mocked(eventsApi.listEvents).mockResolvedValue(makeListResponse(items, 1))
    const store = useEventsStore()
    await store.fetch()
    expect(store.items).toHaveLength(1)
    expect(store.total).toBe(1)
    expect(store.loading).toBe(false)
  })

  it('fetch sets error on API failure', async () => {
    vi.mocked(eventsApi.listEvents).mockRejectedValue(new Error('500 Internal Server Error'))
    const store = useEventsStore()
    await store.fetch()
    expect(store.error).toBe('500 Internal Server Error')
    expect(store.loading).toBe(false)
  })

  it('fetch uses fallback error message for non-Error throws', async () => {
    vi.mocked(eventsApi.listEvents).mockRejectedValue('oops')
    const store = useEventsStore()
    await store.fetch()
    expect(store.error).toBe('Fehler beim Laden')
  })

  it('setFilter merges patch and resets offset to 0', () => {
    const store = useEventsStore()
    store.setFilter({ district_id: 'abc', offset: 50 })
    expect(store.filters.district_id).toBe('abc')
    expect(store.filters.offset).toBe(0)
  })

  it('goToPage sets correct offset', () => {
    const store = useEventsStore()
    store.goToPage(3)
    expect(store.filters.offset).toBe(100) // (3-1) * 50
  })

  it('goToPage(1) sets offset to 0', () => {
    const store = useEventsStore()
    store.goToPage(3)
    store.goToPage(1)
    expect(store.filters.offset).toBe(0)
  })

  it('currentPage reflects goToPage', () => {
    const store = useEventsStore()
    store.goToPage(3)
    expect(store.currentPage).toBe(3)
  })
})
