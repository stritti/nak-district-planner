import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import * as integrationsApi from '../api/calendarIntegrations'
import * as districtsApi from '../api/districts'
import { useDistrictsStore } from '../stores/districts'
import CalendarIntegrationsView from './CalendarIntegrationsView.vue'

vi.mock('../api/calendarIntegrations')
vi.mock('../api/districts')

const integration = (
  type: integrationsApi.CalendarType,
): integrationsApi.CalendarIntegrationResponse => ({
  id: `integration-${type}`,
  district_id: 'district-1',
  congregation_id: null,
  name: `Kalender ${type}`,
  type,
  sync_interval: 60,
  capabilities: ['READ'],
  is_active: true,
  last_synced_at: null,
  last_sync_error: null,
  created_at: '2026-10-01T10:00:00Z',
  updated_at: '2026-10-01T10:00:00Z',
  default_category: null,
})

async function mountView(items: integrationsApi.CalendarIntegrationResponse[] = []) {
  vi.mocked(integrationsApi.listIntegrations).mockResolvedValue({ items, total: items.length })
  vi.mocked(districtsApi.listCongregations).mockResolvedValue([])
  const pinia = createPinia()
  setActivePinia(pinia)
  const districts = useDistrictsStore()
  districts.districts = [{ id: 'district-1', name: 'Bezirk' } as never]
  const wrapper = mount(CalendarIntegrationsView, {
    global: { plugins: [pinia] },
    attachTo: document.body,
  })
  await flushPromises()
  return wrapper
}

describe('CalendarIntegrationsView provider options (v1.0: ICS + CalDAV only)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    document.body.innerHTML = ''
  })

  it('offers only ICS and CalDAV; Google/Microsoft are marked "geplant" and disabled', async () => {
    const wrapper = await mountView()
    await wrapper.find('button.btn-primary').trigger('click')
    await flushPromises()

    const options = Array.from(
      document.body.querySelectorAll<HTMLOptionElement>('option[value="ICS"], option[value="CALDAV"], option[value="GOOGLE"], option[value="MICROSOFT"]'),
    )
    const enabled = options.filter((o) => !o.disabled).map((o) => o.value)
    const disabled = options.filter((o) => o.disabled)

    expect(enabled).toEqual(['ICS', 'CALDAV'])
    expect(disabled.map((o) => o.value)).toEqual(['GOOGLE', 'MICROSOFT'])
    for (const option of disabled) expect(option.textContent).toContain('geplant')
    wrapper.unmount()
  })

  it('keeps existing Google integrations visible but disables their manual sync', async () => {
    const wrapper = await mountView([integration('ICS'), integration('GOOGLE')])

    expect(wrapper.text()).toContain('Kalender GOOGLE')
    const syncButtons = wrapper.findAll('button[title*="ynchron"]')
    expect(syncButtons).toHaveLength(2)
    expect(syncButtons[0].attributes('disabled')).toBeUndefined()
    expect(syncButtons[1].attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('in Version 1.0 nicht unterstützt')

    await syncButtons[1].trigger('click')
    expect(integrationsApi.triggerSync).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('does not mention Google or Microsoft in the empty-state hint', async () => {
    const wrapper = await mountView()
    expect(wrapper.text()).not.toMatch(/Google-|Microsoft-/)
    expect(wrapper.text()).toContain('CalDAV')
    wrapper.unmount()
  })
})
