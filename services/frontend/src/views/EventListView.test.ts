import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import * as districtsApi from '../api/districts'
import * as eventsApi from '../api/events'
import * as assignmentsApi from '../api/serviceAssignments'
import * as leadersApi from '../api/leaders'
import { useDistrictsStore } from '../stores/districts'
import { useEventsStore } from '../stores/events'
import EventListView from './EventListView.vue'
import { useAuthStore } from '../stores/auth'

const mocks = vi.hoisted(() => ({
  confirm: vi.fn(),
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
  exportEvents: vi.fn(),
}))


vi.mock('../api/districts')
vi.mock('../api/events')
vi.mock('../api/serviceAssignments')
vi.mock('../api/leaders')
vi.mock('../composables/useConfirm', () => ({
  useConfirm: () => mocks.confirm,
}))
vi.mock('../composables/useToast', () => ({
  useToast: () => ({ success: mocks.toastSuccess, error: mocks.toastError }),
  errorMessage: (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback,
}))
vi.mock('../composables/useExcelExport', () => ({
  exportEventsToExcel: mocks.exportEvents,
}))

const now = '2026-10-05T00:00:00Z'

const district = (id: string, name: string): districtsApi.DistrictResponse => ({
  id,
  name,
  state_code: null,
  created_at: now,
  updated_at: now,
})

const congregation = (id: string, name: string, districtId = 'd1'): districtsApi.CongregationResponse => ({
  id,
  name,
  district_id: districtId,
  group_id: null,
  service_times: [],
  created_at: now,
  updated_at: now,
})

const event = (overrides: Partial<eventsApi.EventResponse> = {}): eventsApi.EventResponse => ({
  id: 'e1',
  title: 'Gottesdienst',
  description: null,
  start_at: '2026-10-05T09:30:00',
  end_at: '2026-10-05T10:30:00',
  district_id: 'd1',
  congregation_id: 'c1',
  category: 'Gottesdienst',
  is_service: true,
  source: 'INTERNAL',
  status: 'ACTIVE',
  approval_status: 'PLANNED',
  visibility: 'INTERNAL',
  applicability: [],
  invitation_source_congregation_id: null,
  invitation_source_event_id: null,
  sync_state: 'CLEAN',
  created_at: now,
  updated_at: now,
  ...overrides,
})

function response(items: eventsApi.EventResponse[], total = items.length): eventsApi.EventListResponse {
  return { items, total, limit: 50, offset: 0 }
}

const baseEvents = [
  event(),
  event({
    id: 'e2',
    title: 'Abgesagter Termin',
    congregation_id: null,
    is_service: false,
    status: 'CANCELLED',
    source: 'EXTERNAL',
    approval_status: 'CONFIRMED',
    invitation_source_congregation_id: 'c2',
    start_at: '2026-10-05T00:00:00',
  }),
  event({
    id: 'holiday',
    title: 'Feiertag',
    congregation_id: null,
    category: 'Feiertag',
    is_service: false,
    start_at: '2026-10-05T00:00:00',
  }),
]

function setup(items = baseEvents) {
  vi.mocked(eventsApi.listEvents).mockResolvedValue(response(items))
  const pinia = createPinia()
  setActivePinia(pinia)
  useAuthStore().user = { sub: 'event-test-user' }
  const districtsStore = useDistrictsStore()
  const eventsStore = useEventsStore()
  const wrapper = mount(EventListView, { global: { plugins: [pinia] } })
  return { wrapper, districtsStore, eventsStore }
}

beforeEach(() => {
  vi.clearAllMocks()
  sessionStorage.clear()
  mocks.confirm.mockResolvedValue(true)
  mocks.exportEvents.mockResolvedValue(undefined)
  vi.mocked(districtsApi.listDistricts).mockResolvedValue([
    district('d1', 'Bezirk Eins'),
    district('d2', 'Bezirk Zwei'),
  ])
  vi.mocked(districtsApi.listCongregations).mockImplementation(async (districtId) => (
    districtId === 'd1'
      ? [congregation('c1', 'Gemeinde Eins'), congregation('c2', 'Gemeinde Zwei')]
      : [congregation('c3', 'Gemeinde Drei', 'd2')]
  ))
  vi.mocked(leadersApi.listLeaders).mockResolvedValue([])
  vi.mocked(districtsApi.listGroups).mockResolvedValue([
    { id: 'g1', name: 'Gruppe Eins', district_id: 'd1', created_at: now, updated_at: now },
  ])
})

describe('EventListView', () => {
  it('restores controls and the matching API query after remounting with fresh stores', async () => {
    const first = setup()
    await flushPromises()
    await first.wrapper.get('#event-status-filter').setValue('CANCELLED')
    await first.wrapper.get('#event-approval-filter').setValue('CONFIRMED')
    await first.wrapper.get('#event-type-filter').setValue('other')
    await first.wrapper.get('#event-congregation-filter').setValue('DISTRICT_ONLY')
    first.wrapper.unmount()

    const second = setup()
    await flushPromises()
    expect((second.wrapper.get('#event-status-filter').element as HTMLSelectElement).value).toBe('CANCELLED')
    expect((second.wrapper.get('#event-approval-filter').element as HTMLSelectElement).value).toBe('CONFIRMED')
    expect(second.eventsStore.filters).toMatchObject({
      district_id: 'd1', status: 'CANCELLED', approval_status: 'CONFIRMED',
      is_service: false, only_district_level: true,
    })
    expect(eventsApi.listEvents).toHaveBeenLastCalledWith(expect.objectContaining({
      status: 'CANCELLED', approval_status: 'CONFIRMED', is_service: false,
    }))
    second.wrapper.unmount()
  })

  it('restores each district and drops unavailable IDs without losing valid filters', async () => {
    sessionStorage.setItem('planner.view-settings.v1:' + JSON.stringify(['event-test-user', 'events', 'd1']),
      JSON.stringify({ group: 'deleted', congregation: 'deleted', status: 'ACTIVE' }))
    const ctx = setup()
    await flushPromises()
    expect(ctx.eventsStore.filters.group_id).toBeUndefined()
    expect(ctx.eventsStore.filters.congregation_id).toBeUndefined()
    expect(ctx.eventsStore.filters.status).toBe('ACTIVE')
    ctx.districtsStore.selectedDistrictId = 'd2'
    await flushPromises()
    expect(ctx.eventsStore.filters.status).toBeUndefined()
    await ctx.wrapper.get('#event-status-filter').setValue('CANCELLED')
    ctx.districtsStore.selectedDistrictId = 'd1'
    await flushPromises()
    expect(ctx.eventsStore.filters.status).toBe('ACTIVE')
    ctx.wrapper.unmount()
  })

  it('shows the responsible person and flags services without a Dienstleiter', async () => {
    const responsible = { assignment_id: 'a1', leader_id: 'l1', name: 'Pr. Muster', status: 'ASSIGNED' as const }
    const { wrapper } = setup([event({ responsible }), event({ id: 'e9', title: 'Ohne' })])
    await flushPromises()

    const cells = wrapper.findAll('[data-testid="responsible-cell"]')
    expect(cells[0].text()).toBe('Pr. Muster')
    expect(cells[1].text()).toBe('Lücke')
  })

  it('assigns, changes and clears the responsible person from the edit dialog', async () => {
    vi.mocked(eventsApi.updateEvent).mockImplementation(async () => event())
    vi.mocked(assignmentsApi.createAssignment).mockResolvedValue({
      id: 'a1', event_id: 'e1', leader_id: null, leader_name: 'Pr. Frei', status: 'ASSIGNED',
      created_at: now, updated_at: now,
    })
    const { wrapper, eventsStore } = setup([event()])
    await flushPromises()

    const save = async () => {
      await wrapper.find('.modal-panel').findAll('button').find((b) => b.text() === 'Speichern')!.trigger('click')
      await flushPromises()
    }
    await wrapper.get('button[title="Zuordnung bearbeiten"]').trigger('click')
    await flushPromises()
    await wrapper.get('input[placeholder="Name eingeben oder auswählen…"]').setValue('Pr. Frei')
    await save()
    expect(assignmentsApi.createAssignment).toHaveBeenCalledWith(
      'e1', { leaderId: null, leaderName: 'Pr. Frei', confirmWarnings: undefined },
    )
    expect(eventsStore.items[0].responsible?.name).toBe('Pr. Frei')

    vi.mocked(assignmentsApi.deleteAssignment).mockResolvedValue()
    await wrapper.get('button[title="Zuordnung bearbeiten"]').trigger('click')
    await flushPromises()
    await wrapper.get('input[placeholder="Name eingeben oder auswählen…"]').setValue('')
    await save()
    expect(assignmentsApi.deleteAssignment).toHaveBeenCalledWith('e1', 'a1')
    expect(eventsStore.items[0].responsible).toBeNull()
  })

  it('keeps the dialog open with the message when the assignment is rejected', async () => {
    vi.mocked(eventsApi.updateEvent).mockResolvedValue(event())
    vi.mocked(assignmentsApi.createAssignment).mockRejectedValue(new Error('Zuweisung kaputt'))
    const { wrapper } = setup([event()])
    await flushPromises()

    await wrapper.get('button[title="Zuordnung bearbeiten"]').trigger('click')
    await flushPromises()
    await wrapper.get('input[placeholder="Name eingeben oder auswählen…"]').setValue('Pr. Frei')
    await wrapper.find('.modal-panel').findAll('button').find((b) => b.text() === 'Speichern')!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Zuweisung kaputt')
    expect(wrapper.find('.modal-panel').exists()).toBe(true)
  })


  it('loads and renders list events with district, congregation, source and status variants', async () => {
    const { wrapper, eventsStore } = setup()
    await flushPromises()

    expect(eventsStore.total).toBe(3)
    expect(wrapper.text()).toContain('Gottesdienst')
    expect(wrapper.text()).toContain('Gemeinde Eins')
    expect(wrapper.text()).toContain('Abgesagt')
    expect(wrapper.text()).toContain('Import')
    expect(wrapper.text()).toContain('Intern')
    expect(wrapper.text()).toContain('Einladung')
    expect(wrapper.text()).toContain('(Bezirk)')
    expect(eventsApi.listEvents).toHaveBeenCalled()
  })

  it('applies presets and all filter variants to the event store', async () => {
    const { wrapper, eventsStore } = setup()
    await flushPromises()

    const preset = (text: string) => wrapper.findAll('button').find((button) => button.text() === text)!
    await preset('Aktueller Monat').trigger('click')
    expect(eventsStore.filters.from_dt).toBeTruthy()
    expect(eventsStore.filters.to_dt).toBeTruthy()
    await preset('Kommender Monat').trigger('click')
    expect(eventsStore.filters.from_dt).toBeTruthy()
    await preset('Alle').trigger('click')
    expect(eventsStore.filters.from_dt).toBeUndefined()
    expect(eventsStore.filters.to_dt).toBeUndefined()

    let selects = wrapper.findAll('select')
    await selects[1].setValue('DISTRICT_ONLY')
    expect(eventsStore.filters.only_district_level).toBe(true)
    expect(eventsStore.filters.congregation_id).toBeUndefined()

    selects = wrapper.findAll('select')
    await selects[2].setValue('g1')
    expect(eventsStore.filters.group_id).toBe('g1')
    expect(eventsStore.filters.only_district_level).toBe(false)

    selects = wrapper.findAll('select')
    await selects[3].setValue('CANCELLED')
    await selects[4].setValue('CONFIRMED')
    await selects[5].setValue('service')
    expect(eventsStore.filters.status).toBe('CANCELLED')
    expect(eventsStore.filters.approval_status).toBe('CONFIRMED')
    expect(eventsStore.filters.is_service).toBe(true)

    await wrapper.findAll('select')[5].setValue('other')
    expect(eventsStore.filters.is_service).toBe(false)
    await wrapper.findAll('select')[5].setValue('')
    expect(eventsStore.filters.is_service).toBeUndefined()
  })

  it('switches between week and month views, navigates periods and merges district holidays', async () => {
    const { wrapper } = setup()
    await flushPromises()

    await wrapper.findAll('select')[1].setValue('c1')
    vi.mocked(eventsApi.listEvents).mockResolvedValue(response([
      ...baseEvents,
      event({ id: 'e3', title: 'Termin Drei', category: 'Sonstiges', is_service: false }),
      event({ id: 'e4', title: 'Termin Vier', category: 'Sonstiges', is_service: false }),
      event({ id: 'e5', title: 'Termin Fünf', category: 'Sonstiges', is_service: false }),
    ]))

    await wrapper.findAll('button').find((button) => button.text() === 'Woche')!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toMatch(/\d{2}\.\d{2}\. – \d{2}\.\d{2}\.\d{4}/)
    expect(eventsApi.listEvents).toHaveBeenCalledWith(expect.objectContaining({ congregation_id: 'c1', limit: 500 }))
    expect(eventsApi.listEvents).toHaveBeenCalledWith(expect.objectContaining({ district_id: 'd1', limit: 500 }))

    const navButtons = wrapper.find('.filter-bar').findAll('button')
    await navButtons[0].trigger('click')
    await navButtons[1].trigger('click')
    await wrapper.findAll('button').find((button) => button.text() === 'Heute')!.trigger('click')
    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text() === 'Monat')!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Oktober')
    expect(wrapper.text()).toContain('Feiertag')

    vi.mocked(eventsApi.listEvents).mockRejectedValueOnce(new Error('Kalender down'))
    await wrapper.findAll('button').find((button) => button.text() === 'Heute')!.trigger('click')
    await flushPromises()
  })

  it('requires confirmation before cancellation and updates a list event after saving', async () => {
    const updated = event({ status: 'CANCELLED', category: 'Neu', approval_status: 'CONFIRMED' })
    vi.mocked(eventsApi.updateEvent).mockResolvedValue(updated)
    const { wrapper, eventsStore } = setup([event()])
    await flushPromises()

    await wrapper.get('button[title="Zuordnung bearbeiten"]').trigger('click')
    await flushPromises()
    const modal = wrapper.find('.modal-panel')
    const selects = modal.findAll('select')
    await selects[0].setValue('')
    await selects[1].setValue('CANCELLED')
    await selects[2].setValue('CONFIRMED')
    await modal.get('input[placeholder="z. B. Gottesdienst"]').setValue('Neu')

    mocks.confirm.mockResolvedValueOnce(false)
    await modal.findAll('button').find((button) => button.text() === 'Speichern')!.trigger('click')
    await flushPromises()
    expect(eventsApi.updateEvent).not.toHaveBeenCalled()

    mocks.confirm.mockResolvedValueOnce(true)
    await modal.findAll('button').find((button) => button.text() === 'Speichern')!.trigger('click')
    await flushPromises()
    expect(eventsApi.updateEvent).toHaveBeenCalledWith('e1', expect.objectContaining({
      congregation_id: null,
      status: 'CANCELLED',
      approval_status: 'CONFIRMED',
      category: 'Neu',
      applicability: [],
    }))
    expect(eventsStore.items[0].status).toBe('CANCELLED')
    expect(mocks.toastSuccess).toHaveBeenCalledWith('Termin gespeichert', 'Gottesdienst')
  })

  it('updates calendar events and surfaces edit failures without closing the modal', async () => {
    const { wrapper } = setup([event()])
    await flushPromises()
    await wrapper.findAll('button').find((button) => button.text() === 'Woche')!.trigger('click')
    await flushPromises()

    const pill = wrapper.findAll('[class*="cursor-pointer"]').find((node) => node.text().includes('Gottesdienst'))!
    await pill.trigger('click')
    await flushPromises()
    const modal = wrapper.find('.modal-panel')
    vi.mocked(eventsApi.updateEvent).mockRejectedValueOnce(new Error('Speichern kaputt'))
    await modal.findAll('button').find((button) => button.text() === 'Speichern')!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Speichern kaputt')
    expect(mocks.toastError).toHaveBeenCalled()

    vi.mocked(eventsApi.updateEvent).mockResolvedValueOnce(event({ title: 'Geändert' }))
    await modal.findAll('select')[1].setValue('ACTIVE')
    await modal.findAll('button').find((button) => button.text() === 'Speichern')!.trigger('click')
    await flushPromises()
    expect(mocks.toastSuccess).toHaveBeenCalledWith('Termin gespeichert', 'Geändert')
  })

  it('exports all matching events and warns when the safety cap truncates the result', async () => {
    const { wrapper, eventsStore } = setup([event()])
    await flushPromises()
    eventsStore.total = 501
    vi.mocked(eventsApi.listEvents).mockResolvedValueOnce(response([event()], 501))

    await wrapper.findAll('button').find((button) => button.text().includes('Excel'))!.trigger('click')
    await flushPromises()

    expect(eventsApi.listEvents).toHaveBeenCalledWith(expect.objectContaining({ limit: 500, offset: 0 }))
    expect(mocks.exportEvents).toHaveBeenCalledWith([expect.objectContaining({ id: 'e1' })], 'Ereignisse.xlsx')
    expect(wrapper.text()).toContain('ersten 500 von 501')
  })
})
