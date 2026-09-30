import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import EventHooksPanel from '@/components/EventHooksPanel.vue'
import * as api from '@/api/eventHooks'

vi.mock('@/api/eventHooks')

const hook: api.EventHook = {
  id: 'hook-1',
  district_id: 'district-a',
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
  { event_type: 'EXTERNAL_EVENT_DETECTED', placeholders: ['event_title', 'source'] },
]

async function mountPanel(hooks: api.EventHook[] = [hook]) {
  vi.mocked(api.listEventHooks).mockResolvedValue(hooks)
  vi.mocked(api.listEventTypes).mockResolvedValue(types)
  const wrapper = mount(EventHooksPanel, { props: { districtId: 'district-a' } })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.resetAllMocks()
  setActivePinia(createPinia())
})

describe('EventHooksPanel', () => {
  it('lists hooks with readable event and role labels', async () => {
    const wrapper = await mountPanel()
    const row = wrapper.get('[data-testid="event-hook-hook-1"]')
    expect(row.text()).toContain('Fehler bei Kalender-Synchronisation')
    expect(row.text()).toContain('Planer')
  })

  it('shows an empty state', async () => {
    const wrapper = await mountPanel([])
    expect(wrapper.text()).toContain('Noch keine Benachrichtigungen angelegt.')
  })

  it('shows the placeholders of the selected event type', async () => {
    const wrapper = await mountPanel()
    expect(wrapper.get('[data-testid="placeholders"]').text()).toContain('{event_title}, {source}')
    await wrapper.get('select[name="event_type"]').setValue('SYNC_ERROR')
    expect(wrapper.get('[data-testid="placeholders"]').text()).toContain('{error_message}')
  })

  it('creates a hook from the form and resets it', async () => {
    const wrapper = await mountPanel([])
    vi.mocked(api.createEventHook).mockResolvedValue({ ...hook, event_type: 'EXTERNAL_EVENT_DETECTED' })

    await wrapper.get('input[name="subject"]').setValue('Neu: {event_title}')
    await wrapper.get('textarea[name="body"]').setValue('Quelle: {source}')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(api.createEventHook).toHaveBeenCalledWith('district-a', {
      event_type: 'EXTERNAL_EVENT_DETECTED',
      recipient_role: 'DISTRICT_ADMIN',
      subject_template: 'Neu: {event_title}',
      body_template: 'Quelle: {source}',
      is_active: true,
    })
    expect((wrapper.get('input[name="subject"]').element as HTMLInputElement).value).toBe('')
  })

  it('edits a hook without sending the immutable event type', async () => {
    const wrapper = await mountPanel()
    vi.mocked(api.updateEventHook).mockResolvedValue(hook)

    await wrapper.get('[data-testid="event-hook-hook-1"] button').trigger('click')
    expect(wrapper.get('select[name="event_type"]').attributes('disabled')).toBeDefined()
    await wrapper.get('input[name="subject"]').setValue('Geändert')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(api.updateEventHook).toHaveBeenCalledWith('district-a', 'hook-1', {
      recipient_role: 'PLANNER',
      subject_template: 'Geändert',
      body_template: '{error_message}',
      is_active: true,
    })
  })

  it('keeps the form input when saving fails', async () => {
    const wrapper = await mountPanel([])
    vi.mocked(api.createEventHook).mockRejectedValue(new Error('422 Unsupported event placeholder'))

    await wrapper.get('input[name="subject"]').setValue('{leader_name}')
    await wrapper.get('textarea[name="body"]').setValue('x')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain('422')
    expect((wrapper.get('input[name="subject"]').element as HTMLInputElement).value).toBe('{leader_name}')
  })

  it('toggles activation via deactivate and full update', async () => {
    const wrapper = await mountPanel()
    vi.mocked(api.deactivateEventHook).mockResolvedValue(undefined)
    const checkbox = wrapper.get('[data-testid="event-hook-hook-1"] input[type="checkbox"]')

    await checkbox.trigger('change')
    await flushPromises()
    expect(api.deactivateEventHook).toHaveBeenCalledWith('district-a', 'hook-1')

    vi.mocked(api.updateEventHook).mockResolvedValue(hook)
    await wrapper.get('[data-testid="event-hook-hook-1"] input[type="checkbox"]').trigger('change')
    await flushPromises()
    expect(api.updateEventHook).toHaveBeenCalledWith('district-a', 'hook-1', {
      recipient_role: 'PLANNER',
      subject_template: 'Fehler {integration_name}',
      body_template: '{error_message}',
      is_active: true,
    })
  })

  it('reloads and resets the form when the district changes', async () => {
    const wrapper = await mountPanel()
    await wrapper.get('input[name="subject"]').setValue('halb fertig')

    await wrapper.setProps({ districtId: 'district-b' })
    await flushPromises()

    expect(api.listEventHooks).toHaveBeenLastCalledWith('district-b')
    expect((wrapper.get('input[name="subject"]').element as HTMLInputElement).value).toBe('')
  })
})
