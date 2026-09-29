import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import * as candidatesApi from '../api/externalCandidates'
import { useExternalCandidatesStore } from './externalCandidates'

vi.mock('../api/externalCandidates')

const candidate = (id = 'candidate-1'): candidatesApi.ExternalEventCandidate => ({
  id,
  district_id: 'district-1',
  calendar_integration_id: 'integration-1',
  external_event_id: 'external-1',
  source: 'GOOGLE',
  congregation_id: null,
  title: 'Externer Gottesdienst',
  category: 'Gottesdienst',
  start_at: '2026-10-04T09:00:00Z',
  end_at: '2026-10-04T10:00:00Z',
  event_date: '2026-10-04',
  event_time: '09:00:00',
  description: null,
  status: 'PENDING',
  matched_slot_id: null,
  created_at: '2026-09-29T10:00:00Z',
  updated_at: '2026-09-29T10:00:00Z',
  reviewed_at: null,
  reviewed_by: null,
})

describe('useExternalCandidatesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('loads pending candidates and clears loading afterwards', async () => {
    vi.mocked(candidatesApi.listExternalCandidates).mockResolvedValue([candidate()])
    const store = useExternalCandidatesStore()

    const pending = store.fetchPending('district-1')
    expect(store.loading).toBe(true)
    await pending

    expect(candidatesApi.listExternalCandidates).toHaveBeenCalledWith('district-1')
    expect(store.items).toHaveLength(1)
    expect(store.error).toBeNull()
    expect(store.loading).toBe(false)
  })

  it('reports load failures and keeps the previous list intact', async () => {
    vi.mocked(candidatesApi.listExternalCandidates).mockRejectedValue(new Error('Backend nicht erreichbar'))
    const store = useExternalCandidatesStore()
    store.items = [candidate()]

    await store.fetchPending('district-1')

    expect(store.items).toHaveLength(1)
    expect(store.error).toBe('Backend nicht erreichbar')
    expect(store.loading).toBe(false)
  })

  it('uses a fallback message for non-Error load failures', async () => {
    vi.mocked(candidatesApi.listExternalCandidates).mockRejectedValue('failed')
    const store = useExternalCandidatesStore()

    await store.fetchPending('district-1')

    expect(store.error).toBe('Kandidaten konnten nicht geladen werden')
  })

  it('accepts a candidate and removes only the reviewed item', async () => {
    const first = candidate('candidate-1')
    const second = candidate('candidate-2')
    vi.mocked(candidatesApi.acceptExternalCandidate).mockResolvedValue({ ...first, status: 'ACCEPTED' })
    const store = useExternalCandidatesStore()
    store.items = [first, second]

    const pending = store.acceptAndCreate(first.id)
    expect(store.reviewingId).toBe(first.id)
    const result = await pending

    expect(candidatesApi.acceptExternalCandidate).toHaveBeenCalledWith(first.id)
    expect(result?.status).toBe('ACCEPTED')
    expect(store.items).toEqual([second])
    expect(store.reviewingId).toBeNull()
  })

  it('dismisses a candidate and removes it from the pending list', async () => {
    const item = candidate()
    vi.mocked(candidatesApi.dismissExternalCandidate).mockResolvedValue({ ...item, status: 'DISMISSED' })
    const store = useExternalCandidatesStore()
    store.items = [item]

    await store.dismiss(item.id)

    expect(candidatesApi.dismissExternalCandidate).toHaveBeenCalledWith(item.id)
    expect(store.items).toEqual([])
    expect(store.reviewingId).toBeNull()
  })

  it('keeps a candidate and reports a review failure', async () => {
    const item = candidate()
    vi.mocked(candidatesApi.acceptExternalCandidate).mockRejectedValue(new Error('Konflikt'))
    const store = useExternalCandidatesStore()
    store.items = [item]

    const result = await store.acceptAndCreate(item.id)

    expect(result).toBeNull()
    expect(store.items).toEqual([item])
    expect(store.error).toBe('Konflikt')
    expect(store.reviewingId).toBeNull()
  })

  it('uses a fallback message for non-Error review failures', async () => {
    vi.mocked(candidatesApi.dismissExternalCandidate).mockRejectedValue('failed')
    const store = useExternalCandidatesStore()

    await store.dismiss('candidate-1')

    expect(store.error).toBe('Prüfung konnte nicht gespeichert werden')
  })
})
