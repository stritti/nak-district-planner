import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useEventHooksStore } from './eventHooks'
import * as api from '../api/eventHooks'

vi.mock('../api/eventHooks')

const district = 'district-a'
const hook: api.EventHook = {
  id: 'hook-1',
  district_id: district,
  event_type: 'SYNC_ERROR',
  recipient_role: 'PLANNER',
  subject_template: 'Fehler {integration_name}',
  body_template: '{error_message}',
  is_active: true,
  created_at: '2026-09-30T08:00:00Z',
  updated_at: '2026-09-30T08:00:00Z',
}
const types: api.EventTypeInfo[] = [
  { event_type: 'SYNC_ERROR', placeholders: ['district_name', 'error_message'] },
]

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(r => { resolve = r })
  return { promise, resolve }
}

beforeEach(() => {
  vi.resetAllMocks()
  setActivePinia(createPinia())
})

describe('useEventHooksStore', () => {
  it('loads hooks and event types of a district', async () => {
    vi.mocked(api.listEventHooks).mockResolvedValue([hook])
    vi.mocked(api.listEventTypes).mockResolvedValue(types)
    const store = useEventHooksStore()

    await store.load(district)

    expect(store.items).toEqual([hook])
    expect(store.placeholdersFor('SYNC_ERROR')).toEqual(['district_name', 'error_message'])
    expect(store.placeholdersFor('PLAN_FINALIZED')).toEqual([])
    expect(store.loading).toBe(false)
  })

  it('shows a load error', async () => {
    vi.mocked(api.listEventHooks).mockRejectedValue(new Error('403 Forbidden'))
    vi.mocked(api.listEventTypes).mockResolvedValue(types)
    const store = useEventHooksStore()
    await store.load(district)
    expect(store.error).toBe('403 Forbidden')
    expect(store.loading).toBe(false)
  })

  it('ignores a stale response after switching district', async () => {
    const slow = deferred<api.EventHook[]>()
    vi.mocked(api.listEventHooks).mockReturnValueOnce(slow.promise).mockResolvedValueOnce([])
    vi.mocked(api.listEventTypes).mockResolvedValue(types)
    const store = useEventHooksStore()

    const first = store.load('district-old')
    await store.load(district)
    slow.resolve([hook])
    await first

    expect(store.districtId).toBe(district)
    expect(store.items).toEqual([])
  })

  it('creates, updates and deactivates hooks in place', async () => {
    vi.mocked(api.listEventHooks).mockResolvedValue([])
    vi.mocked(api.listEventTypes).mockResolvedValue(types)
    const store = useEventHooksStore()
    await store.load(district)

    vi.mocked(api.createEventHook).mockResolvedValue(hook)
    await store.create({ ...hook })
    expect(store.items).toEqual([hook])

    const renamed = { ...hook, subject_template: 'Neu' }
    vi.mocked(api.updateEventHook).mockResolvedValue(renamed)
    await store.update(hook.id, { ...renamed })
    expect(store.items[0]!.subject_template).toBe('Neu')

    vi.mocked(api.deactivateEventHook).mockResolvedValue(undefined)
    await store.deactivate(hook.id)
    expect(store.items[0]!.is_active).toBe(false)
    expect(api.deactivateEventHook).toHaveBeenCalledWith(district, hook.id)
  })

  it('keeps state and rethrows when a write fails', async () => {
    vi.mocked(api.listEventHooks).mockResolvedValue([hook])
    vi.mocked(api.listEventTypes).mockResolvedValue(types)
    const store = useEventHooksStore()
    await store.load(district)
    vi.mocked(api.updateEventHook).mockRejectedValue(new Error('422 Invalid template'))

    await expect(store.update(hook.id, { ...hook })).rejects.toThrow('422')

    expect(store.error).toBe('422 Invalid template')
    expect(store.items).toEqual([hook])
    expect(store.saving).toBe(false)
  })

  it('uses a fallback message for non-Error failures', async () => {
    vi.mocked(api.listEventHooks).mockResolvedValue([])
    vi.mocked(api.listEventTypes).mockResolvedValue(types)
    const store = useEventHooksStore()
    await store.load(district)
    vi.mocked(api.createEventHook).mockRejectedValue('boom')

    await expect(store.create({ ...hook })).rejects.toBe('boom')
    expect(store.error).toBe('Benachrichtigung konnte nicht angelegt werden')
  })

  it('refuses writes without a selected district', async () => {
    const store = useEventHooksStore()
    await expect(store.deactivate('x')).rejects.toThrow('Kein Bezirk')
    expect(api.deactivateEventHook).not.toHaveBeenCalled()
  })
})
