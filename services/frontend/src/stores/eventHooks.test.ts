// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useEventHooksStore } from './eventHooks'
import * as api from '../api/eventHooks'
import { ApiError } from '../api/errors'

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
  revision: '"hook-1:v1"',
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

    const renamed = { ...hook, subject_template: 'Neu', revision: '"hook-1:v2"' }
    vi.mocked(api.updateEventHook).mockResolvedValue(renamed)
    await store.update(hook.id, { ...renamed })
    expect(store.items[0]!.subject_template).toBe('Neu')
    expect(vi.mocked(api.updateEventHook).mock.calls[0]![3]).toBe(hook.revision)

    vi.mocked(api.deactivateEventHook).mockResolvedValue({ ...renamed, is_active: false, revision: '"hook-1:v3"' })
    await store.deactivate(hook.id)
    expect(store.items[0]!.is_active).toBe(false)
    expect(store.items[0]!.revision).toBe('"hook-1:v3"')
    // The deactivation continues from the revision returned by the previous write.
    expect(api.deactivateEventHook).toHaveBeenCalledWith(district, hook.id, '"hook-1:v2"')
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

  it.each([
    ['update', 412],
    ['update', 428],
    ['deactivate', 412],
  ] as const)('refreshes the hooks and explains a stale %s (%i)', async (operation, status) => {
    const remote = { ...hook, subject_template: 'Remote', revision: '"hook-1:v9"' }
    vi.mocked(api.listEventHooks).mockResolvedValueOnce([hook]).mockResolvedValueOnce([remote])
    vi.mocked(api.listEventTypes).mockResolvedValue(types)
    const stale = new ApiError(status, 'Precondition', { detail: 'x' })
    vi.mocked(api.updateEventHook).mockRejectedValue(stale)
    vi.mocked(api.deactivateEventHook).mockRejectedValue(stale)
    const store = useEventHooksStore()
    await store.load(district)

    const call = operation === 'update'
      ? store.update(hook.id, { recipient_role: 'PLANNER', subject_template: 'x', body_template: 'y', is_active: true })
      : store.deactivate(hook.id)
    await expect(call).rejects.toBe(stale)

    expect(store.error).toContain('zwischenzeitlich geändert')
    expect(store.items).toEqual([remote])
    expect(store.saving).toBe(false)
  })

  it('keeps the stale-write message when the refresh itself fails', async () => {
    vi.mocked(api.listEventHooks).mockResolvedValueOnce([hook]).mockRejectedValueOnce(new Error('offline'))
    vi.mocked(api.listEventTypes).mockResolvedValue(types)
    vi.mocked(api.deactivateEventHook).mockRejectedValue(new ApiError(412, 'Precondition', {}))
    const store = useEventHooksStore()
    await store.load(district)

    await expect(store.deactivate(hook.id)).rejects.toBeInstanceOf(ApiError)

    expect(store.error).toContain('zwischenzeitlich geändert')
    expect(store.items).toEqual([hook])
  })
})
