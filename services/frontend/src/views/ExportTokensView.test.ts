import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../api/exportTokens')
vi.mock('../api/districts')

import * as exportApi from '../api/exportTokens'
import * as districtApi from '../api/districts'
import { useDistrictsStore } from '../stores/districts'
import { useToastStore } from '../stores/toast'
import ExportTokensView from './ExportTokensView.vue'

const district = {
  id: 'district-1',
  name: 'Tuttlingen',
  state_code: 'BW',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}
const congregation = {
  id: 'congregation-1',
  name: 'Stockach',
  district_id: 'district-1',
  group_id: null,
  service_times: [],
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}
const token = (overrides: Partial<exportApi.ExportTokenResponse> = {}): exportApi.ExportTokenResponse => ({
  id: 'token-1',
  token: 'secret-path-token',
  label: 'Bezirk öffentlich',
  token_type: 'PUBLIC',
  district_id: 'district-1',
  congregation_id: null,
  leader_id: null,
  created_at: '2026-01-01T00:00:00Z',
  ...overrides,
})

function mountView(options: { districts?: typeof district[] } = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const districts = useDistrictsStore()
  districts.districts = options.districts ?? [district]
  districts.fetchDistricts = vi.fn().mockResolvedValue(undefined)
  const toast = useToastStore()
  vi.spyOn(toast, 'success')
  vi.spyOn(toast, 'error')
  return { wrapper: mount(ExportTokensView, { global: { plugins: [pinia] } }), districts, toast }
}

describe('ExportTokensView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(districtApi.listCongregations).mockResolvedValue([congregation])
    vi.mocked(exportApi.listExportTokens).mockResolvedValue([])
    vi.mocked(exportApi.createExportToken).mockResolvedValue(token())
    vi.mocked(exportApi.deleteExportToken).mockResolvedValue(undefined)
  })

  it('loads districts when necessary and shows the empty state', async () => {
    const { wrapper, districts } = mountView({ districts: [] })
    await flushPromises()

    expect(districts.fetchDistricts).toHaveBeenCalledOnce()
    expect(exportApi.listExportTokens).toHaveBeenCalledOnce()
    expect(wrapper.text()).toContain('Noch keine Export-Tokens angelegt.')
  })

  it('shows loading and API error states', async () => {
    let reject!: (error: Error) => void
    vi.mocked(exportApi.listExportTokens).mockReturnValue(new Promise((_resolve, rejectPromise) => {
      reject = rejectPromise
    }))
    const { wrapper } = mountView()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Lade…')

    reject(new Error('Tokens konnten nicht geladen werden'))
    await flushPromises()
    expect(wrapper.text()).toContain('Tokens konnten nicht geladen werden')
  })

  it('renders token labels, tenant names and default filter semantics', async () => {
    vi.mocked(exportApi.listExportTokens).mockResolvedValue([
      token({ congregation_id: 'congregation-1' }),
      token({ id: 'token-2', label: 'Intern', token_type: 'INTERNAL', leader_id: 'leader-1' }),
    ])
    const { wrapper } = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('Bezirk öffentlich')
    expect(wrapper.text()).toContain('Tuttlingen')
    expect(wrapper.text()).toContain('Stockach')
    expect(wrapper.text()).toContain('Öffentlich')
    expect(wrapper.text()).toContain('Intern')
    expect(wrapper.html()).toContain('/api/v1/export/secret-path-token/calendar.ics')
  })

  it('opens and resets the create form', async () => {
    const { wrapper } = mountView()
    await flushPromises()

    await wrapper.get('button.btn-primary').trigger('click')

    expect(wrapper.text()).toContain('Neuer Export-Token')
    const inputs = wrapper.findAll('.form-input')
    expect(inputs).toHaveLength(4)
    expect((inputs[0].element as HTMLInputElement).value).toBe('')
    expect((inputs[2].element as HTMLSelectElement).value).toBe('')
  })

  it('loads congregations for the selected district and creates a scoped token', async () => {
    const { wrapper, toast } = mountView()
    await flushPromises()
    await wrapper.get('button.btn-primary').trigger('click')
    const fields = wrapper.findAll('.form-input')
    await fields[0].setValue('  Gemeinde Stockach  ')
    await fields[1].setValue('INTERNAL')
    await fields[2].setValue('district-1')
    await fields[2].trigger('change')
    await flushPromises()
    expect(districtApi.listCongregations).toHaveBeenCalledWith('district-1')
    await fields[3].setValue('congregation-1')

    const save = wrapper.findAll('button').find((button) => button.text().includes('Token erstellen'))
    expect(save).toBeTruthy()
    await save!.trigger('click')
    await flushPromises()

    expect(exportApi.createExportToken).toHaveBeenCalledWith({
      label: 'Gemeinde Stockach',
      token_type: 'INTERNAL',
      district_id: 'district-1',
      congregation_id: 'congregation-1',
    })
    expect(toast.success).toHaveBeenCalledWith('Export-Token erstellt', 'Bezirk öffentlich')
    expect(wrapper.text()).not.toContain('Neuer Export-Token')
  })

  it('keeps the create dialog open and displays creation errors', async () => {
    vi.mocked(exportApi.createExportToken).mockRejectedValue(new Error('Speichern fehlgeschlagen'))
    const { wrapper } = mountView()
    await flushPromises()
    await wrapper.get('button.btn-primary').trigger('click')
    const fields = wrapper.findAll('.form-input')
    await fields[0].setValue('Token')
    await fields[2].setValue('district-1')
    const save = wrapper.findAll('button').find((button) => button.text().includes('Token erstellen'))!
    await save.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Speichern fehlgeschlagen')
    expect(wrapper.text()).toContain('Neuer Export-Token')
  })

  it('deletes a token after confirmation and reports success', async () => {
    vi.mocked(exportApi.listExportTokens).mockResolvedValue([token()])
    const { wrapper, toast } = mountView()
    await flushPromises()
    await wrapper.get('button[title="Token löschen"]').trigger('click')
    await wrapper.vm.$nextTick()

    const confirm = wrapper.findAll('button').find((button) => button.text().includes('Endgültig löschen'))
    expect(confirm).toBeTruthy()
    await confirm!.trigger('click')
    await flushPromises()

    expect(exportApi.deleteExportToken).toHaveBeenCalledWith('token-1')
    expect(toast.success).toHaveBeenCalledWith('Export-Token gelöscht', 'Bezirk öffentlich')
    expect(wrapper.text()).toContain('Noch keine Export-Tokens angelegt.')
  })

  it('reports deletion failure and keeps the token visible', async () => {
    vi.mocked(exportApi.listExportTokens).mockResolvedValue([token()])
    vi.mocked(exportApi.deleteExportToken).mockRejectedValue(new Error('Provider nicht erreichbar'))
    const { wrapper, toast } = mountView()
    await flushPromises()
    await wrapper.get('button[title="Token löschen"]').trigger('click')
    await wrapper.vm.$nextTick()
    const confirm = wrapper.findAll('button').find((button) => button.text().includes('Endgültig löschen'))!
    await confirm.trigger('click')
    await flushPromises()

    expect(toast.error).toHaveBeenCalledWith('Löschen fehlgeschlagen', 'Provider nicht erreichbar')
    expect(wrapper.text()).toContain('Bezirk öffentlich')
  })
})
