import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import * as calendarApi from '../api/calendarIntegrations'
import * as districtsApi from '../api/districts'
import { useDistrictsStore } from '../stores/districts'
import CalendarIntegrationsView from './CalendarIntegrationsView.vue'

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
})

describe('CalendarIntegrationsView', () => {
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

  it('validates provider-specific create credentials and surfaces create errors', async () => {
    vi.mocked(calendarApi.createIntegration).mockRejectedValueOnce(new Error('Anlegen fehlgeschlagen'))
    const { wrapper } = setup([])
    await flushPromises()
    await wrapper.get('button.btn-primary').trigger('click')
    const modal = wrapper.findAll('.modal-panel').find((node) => node.text().includes('Neue Kalender-Integration'))!
    const selects = modal.findAll('select')
    await selects[0].setValue('d1')
    await modal.get('input[placeholder="z. B. Gemeinde-Kalender Nord"]').setValue('Kalender')
    await selects.find((select) => select.findAll('option').some((option) => option.attributes('value') === 'GOOGLE'))!.setValue('GOOGLE')
    await flushPromises()
    const create = modal.findAll('button').find((button) => button.text() === 'Anlegen')!
    expect(create.attributes('disabled')).toBeDefined()

    await modal.get('textarea').setValue('{"access_token":"token"}')
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