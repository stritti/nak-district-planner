import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
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
    vi.clearAllMocks()
    vi.mocked(eventsApi.listEvents).mockResolvedValue(makeListResponse())
  })

  it('initialises with empty state and default pagination', () => {
    const store = useEventsStore()
    expect(store.items).toEqual([])
    expect(store.total).toBe(0)
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
    expect(store.currentPage).toBe(1)
    expect(store.totalPages).toBe(0)
  })

  it('treats a persisted filter without offset as page one', () => {
    const store = useEventsStore()
    store.filters = { district_id: 'district-1' }
    expect(store.currentPage).toBe(1)
  })

  it('rounds totalPages up and stores fetched records', async () => {
    vi.mocked(eventsApi.listEvents).mockResolvedValue(
      makeListResponse([{ id: '1', title: 'Gottesdienst' }], 51),
    )
    const store = useEventsStore()

    await store.fetch()

    expect(eventsApi.listEvents).toHaveBeenCalledWith(store.filters)
    expect(store.items).toHaveLength(1)
    expect(store.total).toBe(51)
    expect(store.totalPages).toBe(2)
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it.each([
    [new Error('500 Internal Server Error'), '500 Internal Server Error'],
    ['oops', 'Fehler beim Laden'],
  ])('records API failures and always clears loading', async (failure, expected) => {
    vi.mocked(eventsApi.listEvents).mockRejectedValueOnce(failure)
    const store = useEventsStore()

    await store.fetch()

    expect(store.error).toBe(expected)
    expect(store.loading).toBe(false)
  })

  it('merges filters, resets pagination and navigates pages', () => {
    const store = useEventsStore()
    store.goToPage(3)
    expect(store.currentPage).toBe(3)
    expect(store.filters.offset).toBe(100)

    store.setFilter({ district_id: 'abc', offset: 50 })
    expect(store.filters.district_id).toBe('abc')
    expect(store.filters.offset).toBe(0)
    expect(store.currentPage).toBe(1)
  })
})
