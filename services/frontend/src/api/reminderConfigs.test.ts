import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from './reminderConfigs'
import { apiFetch } from './client'

vi.mock('./client', () => ({ apiFetch: vi.fn() }))

beforeEach(() => {
  vi.resetAllMocks()
})

const input: api.ReminderConfigInput = {
  day_of_month: 10,
  time_of_day: '10:00',
  subject_template: 'Betreff',
  body_template: 'Nachricht',
  recipient_role: 'PLANNER',
  is_active: true,
}

const path = '/api/v1/districts/district-a/reminder-configs'

describe('reminder configuration API', () => {
  it('lists only the selected district', async () => {
    vi.mocked(apiFetch).mockResolvedValue([])
    expect(await api.listReminderConfigs('district-a')).toEqual([])
    expect(apiFetch).toHaveBeenCalledWith(path)
  })

  it('posts the complete reminder config payload', async () => {
    await api.createReminderConfig('district-a', input)
    expect(apiFetch).toHaveBeenCalledWith(path, {
      method: 'POST', body: JSON.stringify(input),
    })
  })

  it('updates only the selected reminder', async () => {
    await api.updateReminderConfig('district-a', 'reminder-1', { is_active: false })
    expect(apiFetch).toHaveBeenCalledWith(`${path}/reminder-1`, {
      method: 'PUT', body: JSON.stringify({ is_active: false }),
    })
  })

  it('uses soft-delete endpoint and escapes IDs', async () => {
    await api.deleteReminderConfig('district/a', 'reminder/1')
    expect(apiFetch).toHaveBeenCalledWith(
      '/api/v1/districts/district%2Fa/reminder-configs/reminder%2F1',
      { method: 'DELETE' },
    )
  })
})
