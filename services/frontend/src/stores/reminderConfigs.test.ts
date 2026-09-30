import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useReminderConfigsStore } from './reminderConfigs'
import * as api from '../api/reminderConfigs'

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
}

beforeEach(() => {
  vi.resetAllMocks()
  setActivePinia(createPinia())
})

describe('useReminderConfigsStore', () => {
  it('loads an empty list without errors', async () => {
    vi.mocked(api.listReminderConfigs).mockResolvedValue([])
    const store = useReminderConfigsStore()
    await store.load(district)
    expect(store.items).toEqual([])
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
    expect(api.listReminderConfigs).toHaveBeenCalledWith(district)
  })

  it('loads records and reports failures without stale state', async () => {
    vi.mocked(api.listReminderConfigs).mockResolvedValueOnce([existing])
      .mockRejectedValueOnce(new Error('Nicht erreichbar'))
    const store = useReminderConfigsStore()
    await store.load(district)
    expect(store.items).toEqual([existing])
    await store.load(district)
    expect(store.items).toEqual([])
    expect(store.error).toBe('Nicht erreichbar')
    expect(store.loading).toBe(false)
  })

  it('ignores a response for a previously selected district', async () => {
    let release!: (configs: api.ReminderConfig[]) => void
    vi.mocked(api.listReminderConfigs).mockImplementationOnce(() => new Promise(resolve => { release = resolve }))
      .mockResolvedValueOnce([])
    const store = useReminderConfigsStore()
    const first = store.load(district)
    await store.load('district-b')
    release([existing])
    await first
    expect(store.districtId).toBe('district-b')
    expect(store.items).toEqual([])
  })

  it('creates, updates, and soft-deactivates a reminder', async () => {
    vi.mocked(api.listReminderConfigs).mockResolvedValue([])
    vi.mocked(api.createReminderConfig).mockResolvedValue(existing)
    vi.mocked(api.updateReminderConfig).mockResolvedValue({ ...existing, day_of_month: 28 })
    vi.mocked(api.deleteReminderConfig).mockResolvedValue(undefined)
    const store = useReminderConfigsStore()
    await store.load(district)
    await store.create(input)
    expect(store.items).toEqual([existing])
    await store.update(existing.id, { day_of_month: 28 })
    expect(store.items[0].day_of_month).toBe(28)
    await store.deactivate(existing.id)
    expect(store.items[0].is_active).toBe(false)
    expect(store.saving).toBe(false)
  })

  it('requires a selected district before mutating', async () => {
    const store = useReminderConfigsStore()
    await expect(store.create(input)).rejects.toThrow('Kein Bezirk')
    await expect(store.update(existing.id, {})).rejects.toThrow('Kein Bezirk')
    await expect(store.deactivate(existing.id)).rejects.toThrow('Kein Bezirk')
  })

  it('retains existing records after failed changes', async () => {
    vi.mocked(api.listReminderConfigs).mockResolvedValue([existing])
    vi.mocked(api.createReminderConfig).mockRejectedValue(new Error('Create failed'))
    vi.mocked(api.updateReminderConfig).mockRejectedValue(new Error('Update failed'))
    vi.mocked(api.deleteReminderConfig).mockRejectedValue(new Error('Delete failed'))
    const store = useReminderConfigsStore()
    await store.load(district)
    await expect(store.create(input)).rejects.toThrow('Create failed')
    expect(store.items).toEqual([existing])
    await expect(store.update(existing.id, { day_of_month: 30 })).rejects.toThrow('Update failed')
    expect(store.items[0].day_of_month).toBe(31)
    await expect(store.deactivate(existing.id)).rejects.toThrow('Delete failed')
    expect(store.items[0].is_active).toBe(true)
    expect(store.error).toBe('Delete failed')
    expect(store.saving).toBe(false)
  })
})
