// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useReminderConfigsStore } from './reminderConfigs'
import * as api from '../api/reminderConfigs'
import { ApiError } from '../api/errors'

vi.mock('../api/reminderConfigs')

const district = 'district-a'
const input: api.ReminderConfigInput = {
  day_of_month: 31,
  time_of_day: '10:00',
  subject_template: 'Planung {month}',
  body_template: 'Hallo',
  recipient_role: 'PLANNER',
  is_active: true,
}
const existing: api.ReminderConfig = {
  ...input,
  id: 'reminder-1',
  district_id: district,
  created_at: '2026-09-30T08:00:00Z',
  updated_at: '2026-09-30T08:00:00Z',
  revision: '"reminder-1:v1"',
}

beforeEach(() => {
  vi.resetAllMocks()
  setActivePinia(createPinia())
})

describe('useReminderConfigsStore', () => {
  it('loads records and clears loading/error', async () => {
    vi.mocked(api.listReminderConfigs).mockResolvedValue([existing])
    const store = useReminderConfigsStore()

    await store.load(district)

    expect(store.items).toEqual([existing])
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
    expect(api.listReminderConfigs).toHaveBeenCalledWith(district)
  })

  it.each([
    [new Error('Nicht erreichbar'), 'Nicht erreichbar'],
    ['offline', 'Erinnerungen konnten nicht geladen werden'],
  ])('reports load failures without stale records', async (failure, expected) => {
    vi.mocked(api.listReminderConfigs).mockRejectedValueOnce(failure)
    const store = useReminderConfigsStore()
    store.items = [existing]

    await store.load(district)

    expect(store.items).toEqual([])
    expect(store.error).toBe(expected)
    expect(store.loading).toBe(false)
  })

  it('ignores success and failure from a previously selected district', async () => {
    let resolveOld!: (configs: api.ReminderConfig[]) => void
    vi.mocked(api.listReminderConfigs)
      .mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve }))
      .mockResolvedValueOnce([])
    const store = useReminderConfigsStore()
    const first = store.load(district)
    await store.load('district-b')
    resolveOld([existing])
    await first
    expect(store.districtId).toBe('district-b')
    expect(store.items).toEqual([])

    let rejectOld!: (error: unknown) => void
    vi.mocked(api.listReminderConfigs)
      .mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectOld = reject }))
      .mockResolvedValueOnce([])
    const staleFailure = store.load(district)
    await store.load('district-b')
    rejectOld(new Error('stale'))
    await staleFailure
    expect(store.error).toBeNull()
    expect(store.loading).toBe(false)
  })

  it('creates, updates, and soft-deactivates a reminder', async () => {
    vi.mocked(api.listReminderConfigs).mockResolvedValue([])
    vi.mocked(api.createReminderConfig).mockResolvedValue(existing)
    vi.mocked(api.updateReminderConfig).mockResolvedValue({ ...existing, day_of_month: 28, revision: '"reminder-1:v2"' })
    vi.mocked(api.deleteReminderConfig).mockResolvedValue({ ...existing, is_active: false, revision: '"reminder-1:v3"' })
    const store = useReminderConfigsStore()
    await store.load(district)

    await store.create(input)
    expect(store.items).toEqual([existing])
    await store.update(existing.id, { day_of_month: 28 })
    expect(store.items[0].day_of_month).toBe(28)
    expect(api.updateReminderConfig).toHaveBeenCalledWith(district, existing.id, { day_of_month: 28 }, existing.revision)
    await store.deactivate(existing.id)
    expect(store.items[0].is_active).toBe(false)
    // The deactivation continues from the revision returned by the previous write.
    expect(api.deleteReminderConfig).toHaveBeenCalledWith(district, existing.id, '"reminder-1:v2"')
    expect(store.items[0].revision).toBe('"reminder-1:v3"')
    expect(store.saving).toBe(false)
  })

  it('requires a selected district before every mutation', async () => {
    const store = useReminderConfigsStore()
    await expect(store.create(input)).rejects.toThrow('Kein Bezirk')
    await expect(store.update(existing.id, {})).rejects.toThrow('Kein Bezirk')
    await expect(store.deactivate(existing.id)).rejects.toThrow('Kein Bezirk')
  })

  it.each([
    ['create', 'Erinnerung konnte nicht angelegt werden'],
    ['update', 'Erinnerung konnte nicht gespeichert werden'],
    ['deactivate', 'Erinnerung konnte nicht deaktiviert werden'],
  ] as const)('uses fallback error text for non-Error %s failures', async (operation, expected) => {
    vi.mocked(api.listReminderConfigs).mockResolvedValue([existing])
    const store = useReminderConfigsStore()
    await store.load(district)

    if (operation === 'create') {
      vi.mocked(api.createReminderConfig).mockRejectedValueOnce('failure')
      await expect(store.create(input)).rejects.toBe('failure')
    } else if (operation === 'update') {
      vi.mocked(api.updateReminderConfig).mockRejectedValueOnce('failure')
      await expect(store.update(existing.id, {})).rejects.toBe('failure')
    } else {
      vi.mocked(api.deleteReminderConfig).mockRejectedValueOnce('failure')
      await expect(store.deactivate(existing.id)).rejects.toBe('failure')
    }

    expect(store.error).toBe(expected)
    expect(store.saving).toBe(false)
  })

  it('retains existing records after Error failures', async () => {
    vi.mocked(api.listReminderConfigs).mockResolvedValue([existing])
    vi.mocked(api.createReminderConfig).mockRejectedValue(new Error('Create failed'))
    vi.mocked(api.updateReminderConfig).mockRejectedValue(new Error('Update failed'))
    vi.mocked(api.deleteReminderConfig).mockRejectedValue(new Error('Delete failed'))
    const store = useReminderConfigsStore()
    await store.load(district)

    await expect(store.create(input)).rejects.toThrow('Create failed')
    await expect(store.update(existing.id, { day_of_month: 30 })).rejects.toThrow('Update failed')
    await expect(store.deactivate(existing.id)).rejects.toThrow('Delete failed')

    expect(store.items).toEqual([existing])
    expect(store.error).toBe('Delete failed')
    expect(store.saving).toBe(false)
  })

  it('does not apply completed mutations after the district changed', async () => {
    const store = useReminderConfigsStore()
    store.districtId = district
    store.items = [existing]

    let resolveCreate!: (value: api.ReminderConfig) => void
    vi.mocked(api.createReminderConfig).mockImplementationOnce(() => new Promise(resolve => { resolveCreate = resolve }))
    const create = store.create(input)
    store.districtId = 'district-b'
    resolveCreate({ ...existing, id: 'created-late' })
    await create
    expect(store.items).toEqual([existing])

    store.districtId = district
    let resolveUpdate!: (value: api.ReminderConfig) => void
    vi.mocked(api.updateReminderConfig).mockImplementationOnce(() => new Promise(resolve => { resolveUpdate = resolve }))
    const update = store.update(existing.id, { day_of_month: 28 })
    store.districtId = 'district-b'
    resolveUpdate({ ...existing, day_of_month: 28 })
    await update
    expect(store.items[0].day_of_month).toBe(31)

    store.districtId = district
    let resolveDelete!: () => void
    vi.mocked(api.deleteReminderConfig).mockImplementationOnce(() => new Promise(resolve => { resolveDelete = resolve }))
    const deactivate = store.deactivate(existing.id)
    store.districtId = 'district-b'
    resolveDelete()
    await deactivate
    expect(store.items[0].is_active).toBe(true)
  })

  it.each([
    ['update', 412],
    ['update', 428],
    ['deactivate', 412],
  ] as const)('refreshes the list and explains a stale %s (%i)', async (operation, status) => {
    const remote = { ...existing, subject_template: 'Remote', revision: '"reminder-1:v9"' }
    vi.mocked(api.listReminderConfigs).mockResolvedValueOnce([existing]).mockResolvedValueOnce([remote])
    const stale = new ApiError(status, 'Precondition', { detail: 'x' })
    vi.mocked(api.updateReminderConfig).mockRejectedValue(stale)
    vi.mocked(api.deleteReminderConfig).mockRejectedValue(stale)
    const store = useReminderConfigsStore()
    await store.load(district)

    const call = operation === 'update'
      ? store.update(existing.id, { day_of_month: 5 })
      : store.deactivate(existing.id)
    await expect(call).rejects.toBe(stale)

    expect(store.error).toContain('zwischenzeitlich geändert')
    expect(store.items).toEqual([remote])
    expect(store.saving).toBe(false)
  })

  it('uses the revision the editor captured, not the reloaded one', async () => {
    vi.mocked(api.listReminderConfigs).mockResolvedValue([{ ...existing, revision: '"reminder-1:v5"' }])
    vi.mocked(api.updateReminderConfig).mockResolvedValue(existing)
    const store = useReminderConfigsStore()
    await store.load(district)

    await store.update(existing.id, { day_of_month: 5 }, '"reminder-1:v1"')

    expect(api.updateReminderConfig).toHaveBeenCalledWith(district, existing.id, { day_of_month: 5 }, '"reminder-1:v1"')
  })

  it('keeps the stale-write message when the refresh itself fails', async () => {
    vi.mocked(api.listReminderConfigs).mockResolvedValueOnce([existing]).mockRejectedValueOnce(new Error('offline'))
    vi.mocked(api.updateReminderConfig).mockRejectedValue(new ApiError(412, 'Precondition', {}))
    const store = useReminderConfigsStore()
    await store.load(district)

    await expect(store.update(existing.id, {})).rejects.toBeInstanceOf(ApiError)

    expect(store.error).toContain('zwischenzeitlich geändert')
    expect(store.items).toEqual([existing])
  })
})
