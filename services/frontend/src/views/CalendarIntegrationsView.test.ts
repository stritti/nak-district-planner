import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import * as calendarApi from '../api/calendarIntegrations'
import * as districtsApi from '../api/districts'
import { useDistrictsStore } from '../stores/districts'
import CalendarIntegrationsView from './CalendarIntegrationsView.vue'
import { useAuthStore } from '../stores/auth'

vi.mock('../api/calendarIntegrations')
vi.mock('../api/districts')

const integration = (overrides: Partial<calendarApi.CalendarIntegrationResponse> = {}): calendarApi.CalendarIntegrationResponse => ({
  id: 'integration-1',
  district_id: 'd1',
  congregation_id: 'c1',
  name: 'Gemeindekalender',
  type: 'ICS',
  sync_interval: 60,
  capabilities: ['READ'],
  is_active: true,
  last_synced_at: null,
  last_sync_error: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  default_category: 'Gottesdienst',
  ...overrides,
})

const ConfirmDialogStub = defineComponent({
  props: { open: Boolean, message: String },
  emits: ['confirm', 'cancel'],
  setup(props, { emit }) {
    return () => props.open
      ? h('div', { 'data-test': 'confirm-dialog' }, [
          h('span', props.message),
          h('button', { 'data-test': 'confirm-delete', onClick: () => emit('confirm') }, 'confirm'),
          h('button', { 'data-test': 'cancel-delete', onClick: () => emit('cancel') }, 'cancel'),
        ])
      : null
  },
})

const EmptyStateStub = defineComponent({
  emits: ['action'],
  setup(_, { emit }) {
    return () => h('button', { 'data-test': 'empty-action', onClick: () => emit('action') }, 'empty')
  },
})

function setup(items: calendarApi.CalendarIntegrationResponse[] = [integration()]) {
  const pinia = createPinia()
  setActivePinia(pinia)
  useAuthStore().user = { sub: 'calendar-user' }
  const districts = useDistrictsStore()
  districts.districts = [
    { id: 'd1', name: 'Bezirk Eins' },
    { id: 'd2', name: 'Bezirk Zwei' },
  ] as typeof districts.districts
  districts.selectedDistrictId = 'd1'
  vi.spyOn(districts, 'fetchDistricts').mockResolvedValue(undefined)

  vi.mocked(districtsApi.listCongregations).mockResolvedValue([
    { id: 'c1', name: 'Gemeinde A', district_id: 'd1' },
  ] as districtsApi.CongregationResponse[])
  vi.mocked(calendarApi.listIntegrations).mockResolvedValue({ items, total: items.length })

  const wrapper = mount(CalendarIntegrationsView, {
    global: {
      plugins: [pinia],
      stubs: {
        ConfirmDialog: ConfirmDialogStub,
        EmptyState: EmptyStateStub,
      },
    },
  })
  return { wrapper, districts }
}

beforeEach(() => {
  vi.clearAllMocks()
  sessionStorage.clear()
})

describe('CalendarIntegrationsView', () => {
  it('retains an explicitly cleared filter and rejects an inaccessible district', async () => {
    const first = setup()
    await flushPromises()
    await first.wrapper.get('select.form-select').setValue('')
    first.wrapper.unmount()
    const restored = setup()
    await flushPromises()
    expect(calendarApi.listIntegrations).toHaveBeenLastCalledWith(undefined)
    expect((restored.wrapper.get('select.form-select').element as HTMLSelectElement).value).toBe('')
    restored.wrapper.unmount()
    sessionStorage.setItem('planner.view-settings.v1:' + JSON.stringify(['calendar-user', 'calendar-integrations', 'district-filter']),
      JSON.stringify({ district: 'removed' }))
    const changed = setup()
    await flushPromises()
    expect(calendarApi.listIntegrations).toHaveBeenLastCalledWith(undefined)
    changed.wrapper.unmount()
  })

  it('loads selected-district integrations and resolves district/congregation labels', async () => {
    const { wrapper } = setup([integration({ last_synced_at: '2026-10-05T10:00:00Z' })])
    await flushPromises()

    expect(calendarApi.listIntegrations).toHaveBeenCalledWith('d1')
    expect(wrapper.text()).toContain('Gemeindekalender')
    expect(wrapper.text()).toContain('Bezirk Eins')
    expect(wrapper.text()).toContain('Gemeinde A')
    expect(wrapper.text()).toContain('Kategorie: Gottesdienst')
    expect(wrapper.text()).toContain('Letzter Sync:')
  })

  it('reloads when the district filter changes and handles load errors', async () => {
    const { wrapper, districts } = setup()
    await flushPromises()
    vi.mocked(calendarApi.listIntegrations).mockRejectedValueOnce(new Error('Kalender kaputt'))

    await wrapper.get('select.form-select').setValue('d2')
    await flushPromises()

    expect(districts.selectedDistrictId).toBe('d2')
    expect(calendarApi.listIntegrations).toHaveBeenLastCalledWith('d2')
    expect(wrapper.text()).toContain('Kalender kaputt')
  })

  it('renders the empty state and opens the create form from its action', async () => {
    const { wrapper } = setup([])
    await flushPromises()

    expect(wrapper.find('[data-test="empty-action"]').exists()).toBe(true)
    await wrapper.get('[data-test="empty-action"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Neue Kalender-Integration')
  })

  it('synchronizes an integration, renders the result and records sync failures', async () => {
    vi.mocked(calendarApi.triggerSync).mockResolvedValue({
      integration_id: 'integration-1', created: 2, updated: 1, cancelled: 1, auto_matched: 3,
    })
    const { wrapper } = setup()
    await flushPromises()

    await wrapper.get('button[title="Jetzt synchronisieren"]').trigger('click')
    await flushPromises()

    expect(calendarApi.triggerSync).toHaveBeenCalledWith('integration-1')
    expect(wrapper.text()).toContain('+2 neu')
    expect(wrapper.text()).toContain('↔3 zugeordnet')

    vi.mocked(calendarApi.triggerSync).mockRejectedValueOnce(new Error('Provider down'))
    await wrapper.get('button[title="Jetzt synchronisieren"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Provider down')
  })

  it('deletes after confirmation and keeps the item when deletion fails', async () => {
    vi.mocked(calendarApi.deleteIntegration).mockResolvedValue(undefined)
    const { wrapper } = setup()
    await flushPromises()

    await wrapper.get('button[title="Löschen"]').trigger('click')
    expect(wrapper.text()).toContain('Gemeindekalender')
    await wrapper.get('[data-test="confirm-delete"]').trigger('click')
    await flushPromises()

    expect(calendarApi.deleteIntegration).toHaveBeenCalledWith('integration-1')
    expect(wrapper.text()).not.toContain('Gemeindekalender')

    vi.mocked(calendarApi.deleteIntegration).mockRejectedValueOnce(new Error('Delete failed'))
    const second = setup([integration({ id: 'integration-2', name: 'Zweiter Kalender' })]).wrapper
    await flushPromises()
    await second.get('button[title="Löschen"]').trigger('click')
    await second.get('[data-test="confirm-delete"]').trigger('click')
    await flushPromises()
    expect(second.text()).toContain('Zweiter Kalender')
  })

  it('edits ICS metadata and optional credentials without leaking empty credentials', async () => {
    const updated = integration({ name: 'Neu' })
    vi.mocked(calendarApi.updateIntegration).mockResolvedValue(updated)
    const { wrapper } = setup()
    await flushPromises()

    await wrapper.get('button[title="Bearbeiten"]').trigger('click')
    expect(wrapper.text()).toContain('Integration bearbeiten')
    const editModal = wrapper.findAll('.modal-panel').find((node) => node.text().includes('Integration bearbeiten'))!
    await editModal.get('input[type="text"]').setValue('Neu')
    await editModal.get('input[type="url"]').setValue(' https://example.org/feed.ics ')
    await editModal.findAll('button').find((button) => button.text() === 'Speichern')!.trigger('click')
    await flushPromises()

    expect(calendarApi.updateIntegration).toHaveBeenCalledWith('integration-1', expect.objectContaining({
      name: 'Neu',
      credentials: { url: 'https://example.org/feed.ics' },
    }))
    expect(wrapper.text()).toContain('Neu')
  })

  it('creates an ICS integration with trimmed values and selected capabilities', async () => {
    const created = integration({ id: 'created', name: 'Neu' })
    vi.mocked(calendarApi.createIntegration).mockResolvedValue(created)
    const { wrapper } = setup([])
    await flushPromises()

    await wrapper.get('button.btn-primary').trigger('click')
    await flushPromises()
    const createModal = wrapper.findAll('.modal-panel').find((node) => node.text().includes('Neue Kalender-Integration'))!
    const selects = createModal.findAll('select')
    await selects[0].setValue('d1')
    await flushPromises()
    await createModal.get('input[placeholder="z. B. Gemeinde-Kalender Nord"]').setValue(' Neu ')
    await createModal.get('input[placeholder="https://example.com/calendar.ics"]').setValue(' https://example.org/new.ics ')
    await createModal.findAll('button').find((button) => button.text() === 'Anlegen')!.trigger('click')
    await flushPromises()

    expect(calendarApi.createIntegration).toHaveBeenCalledWith(expect.objectContaining({
      district_id: 'd1',
      name: 'Neu',
      type: 'ICS',
      credentials: { url: 'https://example.org/new.ics' },
      capabilities: ['READ'],
    }))
    expect(wrapper.text()).toContain('Neu')
  })

  it('validates CalDAV create credentials and surfaces create errors', async () => {
    vi.mocked(calendarApi.createIntegration).mockRejectedValueOnce(new Error('Anlegen fehlgeschlagen'))
    const { wrapper } = setup([])
    await flushPromises()
    await wrapper.get('button.btn-primary').trigger('click')
    const modal = wrapper.findAll('.modal-panel').find((node) => node.text().includes('Neue Kalender-Integration'))!
    const selects = modal.findAll('select')
    await selects[0].setValue('d1')
    await modal.get('input[placeholder="z. B. Gemeinde-Kalender Nord"]').setValue('Kalender')
    await selects.find((select) => select.findAll('option').some((option) => option.attributes('value') === 'CALDAV'))!.setValue('CALDAV')
    await flushPromises()
    const create = modal.findAll('button').find((button) => button.text() === 'Anlegen')!
    expect(create.attributes('disabled')).toBeDefined()

    await modal.get('input[type="url"]').setValue('https://dav.example.org/cal/')
    expect(create.attributes('disabled')).toBeDefined()
    const inputs = modal.findAll('input')
    const urlIndex = inputs.findIndex((input) => input.attributes('type') === 'url')
    await inputs[urlIndex + 1].setValue('planer') // CalDAV username follows the URL field
    await flushPromises()
    expect(create.attributes('disabled')).toBeUndefined()

    await create.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Anlegen fehlgeschlagen')
  })

  it('imports public holidays and renders import errors', async () => {
    vi.mocked(districtsApi.importFeiertage).mockResolvedValue({ created: 2, updated: 1, skipped: 3 })
    const { wrapper } = setup()
    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text().includes('Deutsche Feiertage importieren'))!.trigger('click')
    const section = wrapper.findAll('.card').find((node) => node.text().includes('Deutsche Feiertage importieren'))!
    const selects = section.findAll('select')
    await selects[0].setValue('d1')
    await selects[1].setValue('BW')
    await section.findAll('button').find((button) => button.text().includes('Importieren'))!.trigger('click')
    await flushPromises()

    expect(districtsApi.importFeiertage).toHaveBeenCalledWith('d1', expect.any(Number), 'BW')
    expect(wrapper.text()).toContain('2 neu')
    expect(wrapper.text()).toContain('3 unverändert')

    vi.mocked(districtsApi.importFeiertage).mockRejectedValueOnce(new Error('Import kaputt'))
    await section.findAll('button').find((button) => button.text().includes('Importieren'))!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Import kaputt')
  })
})

const providerIntegration = (
  type: calendarApi.CalendarType,
): calendarApi.CalendarIntegrationResponse => ({
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

async function mountProviderView(items: calendarApi.CalendarIntegrationResponse[] = []) {
  vi.mocked(calendarApi.listIntegrations).mockResolvedValue({ items, total: items.length })
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
    const wrapper = await mountProviderView()
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
    const wrapper = await mountProviderView([providerIntegration('ICS'), providerIntegration('GOOGLE')])

    expect(wrapper.text()).toContain('Kalender GOOGLE')
    const syncButtons = wrapper.findAll('button[title*="ynchron"]')
    expect(syncButtons).toHaveLength(2)
    expect(syncButtons[0].attributes('disabled')).toBeUndefined()
    expect(syncButtons[1].attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('in Version 1.0 nicht unterstützt')

    await syncButtons[1].trigger('click')
    expect(calendarApi.triggerSync).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('does not mention Google or Microsoft in the empty-state hint', async () => {
    const wrapper = await mountProviderView()
    expect(wrapper.text()).not.toMatch(/Google-|Microsoft-/)
    expect(wrapper.text()).toContain('CalDAV')
    wrapper.unmount()
  })
})
