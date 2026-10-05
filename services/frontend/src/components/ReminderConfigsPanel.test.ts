import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import * as reminderApi from '../api/reminderConfigs'
import type { ReminderConfig } from '../api/reminderConfigs'
import ReminderConfigsPanel from './ReminderConfigsPanel.vue'

vi.mock('../api/reminderConfigs')

const existing: ReminderConfig = {
  id: 'reminder-1',
  district_id: 'district-1',
  day_of_month: 5,
  time_of_day: '08:30:00',
  subject_template: 'Planung {month}',
  body_template: 'Bitte planen',
  recipient_role: 'PLANNER',
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

function setup(items: ReminderConfig[] = []) {
  vi.mocked(reminderApi.listReminderConfigs).mockResolvedValue(items)
  const pinia = createPinia()
  setActivePinia(pinia)
  const wrapper = mount(ReminderConfigsPanel, {
    props: { districtId: 'district-1' },
    global: { plugins: [pinia] },
  })
  return { wrapper }
}

describe('ReminderConfigsPanel', () => {
  beforeEach(() => vi.clearAllMocks())

  it('loads the selected district and shows the empty state', async () => {
    const { wrapper } = setup()
    await flushPromises()

    expect(reminderApi.listReminderConfigs).toHaveBeenCalledWith('district-1')
    expect(wrapper.text()).toContain('Noch keine Erinnerungen angelegt.')
  })

  it('reloads and resets edit state when the district changes', async () => {
    const { wrapper } = setup([existing])
    await flushPromises()
    await wrapper.get('button.btn-secondary').trigger('click')
    expect(wrapper.text()).toContain('Erinnerung bearbeiten')

    vi.mocked(reminderApi.listReminderConfigs).mockResolvedValue([])
    await wrapper.setProps({ districtId: 'district-2' })
    await flushPromises()

    expect(reminderApi.listReminderConfigs).toHaveBeenLastCalledWith('district-2')
    expect(wrapper.text()).toContain('Erinnerung hinzufügen')
  })

  it('creates a reminder from the form and resets defaults afterwards', async () => {
    const created = { ...existing, id: 'created', subject_template: 'Neuer Betreff' }
    vi.mocked(reminderApi.createReminderConfig).mockResolvedValue(created)
    const { wrapper } = setup()
    await flushPromises()

    const textInputs = wrapper.findAll('input')
    await textInputs.find((input) => input.attributes('maxlength') === '500')!.setValue('Neuer Betreff')
    await wrapper.get('textarea').setValue('Neue Nachricht')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(reminderApi.createReminderConfig).toHaveBeenCalledWith(
      'district-1',
      expect.objectContaining({
        subject_template: 'Neuer Betreff',
        body_template: 'Neue Nachricht',
        day_of_month: 10,
        time_of_day: '10:00',
        recipient_role: 'PLANNER',
        is_active: true,
      }),
    )
    expect(wrapper.text()).toContain('Erinnerung hinzufügen')
  })

  it('edits and updates an existing reminder', async () => {
    const updated = { ...existing, subject_template: 'Geändert' }
    vi.mocked(reminderApi.updateReminderConfig).mockResolvedValue(updated)
    const { wrapper } = setup([existing])
    await flushPromises()

    await wrapper.get('button.btn-secondary').trigger('click')
    expect(wrapper.text()).toContain('Erinnerung bearbeiten')
    expect((wrapper.get('input[maxlength="500"]').element as HTMLInputElement).value).toBe('Planung {month}')
    expect((wrapper.get('input[type="time"]').element as HTMLInputElement).value).toBe('08:30')

    await wrapper.get('input[maxlength="500"]').setValue('Geändert')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(reminderApi.updateReminderConfig).toHaveBeenCalledWith(
      'district-1',
      'reminder-1',
      expect.objectContaining({ subject_template: 'Geändert' }),
    )
  })

  it('deactivates active reminders and reactivates inactive reminders', async () => {
    vi.mocked(reminderApi.deleteReminderConfig).mockResolvedValue(undefined)
    vi.mocked(reminderApi.updateReminderConfig).mockImplementation(async (_district, _id, input) => ({
      ...existing,
      ...input,
    }))
    const { wrapper } = setup([existing])
    await flushPromises()

    await wrapper.get('input[type="checkbox"]').trigger('change')
    await flushPromises()
    expect(reminderApi.deleteReminderConfig).toHaveBeenCalledWith('district-1', 'reminder-1')

    await wrapper.get('input[type="checkbox"]').trigger('change')
    await flushPromises()
    expect(reminderApi.updateReminderConfig).toHaveBeenCalledWith(
      'district-1',
      'reminder-1',
      { is_active: true },
    )
  })

  it('keeps store errors visible when load/create/toggle fail', async () => {
    vi.mocked(reminderApi.listReminderConfigs).mockRejectedValue(new Error('Laden fehlgeschlagen'))
    const { wrapper } = setup()
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('Laden fehlgeschlagen')

    vi.mocked(reminderApi.createReminderConfig).mockRejectedValue(new Error('Speichern fehlgeschlagen'))
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('Speichern fehlgeschlagen')
  })
})
