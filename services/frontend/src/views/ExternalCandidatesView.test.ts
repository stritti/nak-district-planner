import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import * as candidatesApi from '../api/externalCandidates'
import { useDistrictsStore } from '../stores/districts'
import ExternalCandidatesView from './ExternalCandidatesView.vue'

vi.mock('../api/externalCandidates')

const candidate = (id = 'candidate-1'): candidatesApi.ExternalEventCandidate => ({
  id,
  district_id: 'district-1',
  calendar_integration_id: 'integration-1',
  external_event_id: `external-${id}`,
  source: 'GOOGLE',
  congregation_id: null,
  title: `Externer Gottesdienst ${id}`,
  category: 'Gottesdienst',
  start_at: '2026-10-04T09:00:00Z',
  end_at: '2026-10-04T10:00:00Z',
  event_date: '2026-10-04',
  event_time: '09:00:00',
  description: 'Aus dem externen Kalender',
  status: 'PENDING',
  matched_slot_id: null,
  created_at: '2026-09-29T10:00:00Z',
  updated_at: '2026-09-29T10:00:00Z',
  reviewed_at: null,
  reviewed_by: null,
})

function mountView(districtId = 'district-1') {
  const pinia = createPinia()
  setActivePinia(pinia)
  const districts = useDistrictsStore()
  districts.setSelectedDistrict(districtId)
  return mount(ExternalCandidatesView, { global: { plugins: [pinia] } })
}

describe('ExternalCandidatesView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('asks for a district and does not fetch when none is selected', async () => {
    const wrapper = mountView('')
    await flushPromises()

    expect(wrapper.text()).toContain('Bitte zuerst einen Bezirk auswählen.')
    expect(candidatesApi.listExternalCandidates).not.toHaveBeenCalled()
  })

  it('shows the loading state while candidates are requested', async () => {
    let resolveRequest!: (value: candidatesApi.ExternalEventCandidate[]) => void
    vi.mocked(candidatesApi.listExternalCandidates).mockReturnValue(
      new Promise((resolve) => { resolveRequest = resolve }),
    )

    const wrapper = mountView()
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Kandidaten werden geladen')
    resolveRequest([])
    await flushPromises()
  })

  it('shows the empty state when there are no pending candidates', async () => {
    vi.mocked(candidatesApi.listExternalCandidates).mockResolvedValue([])

    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('Keine offenen externen Termine.')
  })

  it('shows API errors instead of an empty state', async () => {
    vi.mocked(candidatesApi.listExternalCandidates).mockRejectedValue(new Error('Laden fehlgeschlagen'))

    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('Laden fehlgeschlagen')
    expect(wrapper.text()).not.toContain('Keine offenen externen Termine.')
  })

  it('accepts and creates a planning slot from a candidate', async () => {
    const item = candidate()
    vi.mocked(candidatesApi.listExternalCandidates).mockResolvedValue([item])
    vi.mocked(candidatesApi.acceptExternalCandidate).mockResolvedValue({ ...item, status: 'ACCEPTED' })

    const wrapper = mountView()
    await flushPromises()
    await wrapper.get('button.btn-primary').trigger('click')
    await flushPromises()

    expect(candidatesApi.acceptExternalCandidate).toHaveBeenCalledWith(item.id)
    expect(wrapper.text()).toContain('Keine offenen externen Termine.')
  })

  it('dismisses a candidate', async () => {
    const item = candidate()
    vi.mocked(candidatesApi.listExternalCandidates).mockResolvedValue([item])
    vi.mocked(candidatesApi.dismissExternalCandidate).mockResolvedValue({ ...item, status: 'DISMISSED' })

    const wrapper = mountView()
    await flushPromises()
    await wrapper.get('button.btn-secondary').trigger('click')
    await flushPromises()

    expect(candidatesApi.dismissExternalCandidate).toHaveBeenCalledWith(item.id)
    expect(wrapper.text()).toContain('Keine offenen externen Termine.')
  })

  it('disables every review action while one candidate is being reviewed', async () => {
    const first = candidate('candidate-1')
    const second = candidate('candidate-2')
    let resolveReview!: (value: candidatesApi.ExternalEventCandidate) => void
    vi.mocked(candidatesApi.listExternalCandidates).mockResolvedValue([first, second])
    vi.mocked(candidatesApi.acceptExternalCandidate).mockReturnValue(
      new Promise((resolve) => { resolveReview = resolve }),
    )

    const wrapper = mountView()
    await flushPromises()
    await wrapper.findAll('button.btn-primary')[0].trigger('click')
    await wrapper.vm.$nextTick()

    const actionButtons = wrapper.findAll('button.btn-primary, button.btn-secondary')
    expect(actionButtons).toHaveLength(4)
    expect(actionButtons.every((button) => button.attributes('disabled') !== undefined)).toBe(true)

    resolveReview({ ...first, status: 'ACCEPTED' })
    await flushPromises()
  })

  it('keeps the candidate list visible when a review mutation fails', async () => {
    const item = candidate()
    vi.mocked(candidatesApi.listExternalCandidates).mockResolvedValue([item])
    vi.mocked(candidatesApi.acceptExternalCandidate).mockRejectedValue(new Error('Speichern fehlgeschlagen'))

    const wrapper = mountView()
    await flushPromises()
    await wrapper.get('button.btn-primary').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Speichern fehlgeschlagen')
    expect(wrapper.text()).toContain(item.title)
    expect(wrapper.find('button.btn-primary').exists()).toBe(true)
    expect(candidatesApi.acceptExternalCandidate).toHaveBeenCalledWith(item.id)
  })
})
