// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import * as districtsApi from '../api/districts'
import * as leadersApi from '../api/leaders'
import * as matrixApi from '../api/matrix'
import * as exportTokensApi from '../api/exportTokens'
import { ApiError } from '../api/errors'
import { useAuthStore } from '../stores/auth'
import { useDistrictsStore } from '../stores/districts'
import GettingStartedView from './GettingStartedView.vue'

vi.mock('../api/districts')
vi.mock('../api/leaders')
vi.mock('../api/matrix')
vi.mock('../api/exportTokens')

const district = (id: string, name: string) => ({
  id, name, state_code: null, created_at: '', updated_at: '', revision: '"r"',
}) as districtsApi.DistrictResponse

const Stub = defineComponent({ template: '<div />' })

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'getting-started', component: GettingStartedView },
      { path: '/events', name: 'events', component: Stub },
      { path: '/:rest(.*)*', component: Stub },
    ],
  })
}

async function mountView(role: 'superadmin' | 'PLANNER' | 'VIEWER' = 'superadmin') {
  const auth = useAuthStore()
  auth.isSuperadmin = role === 'superadmin'
  auth.memberships = role === 'superadmin'
    ? []
    : [{ scope_type: 'DISTRICT', scope_id: 'd1', role } as (typeof auth.memberships)[number]]
  const router = makeRouter()
  await router.push('/')
  await router.isReady()
  const wrapper = mount(GettingStartedView, { global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, router }
}

const step = (wrapper: Awaited<ReturnType<typeof mountView>>['wrapper'], id: string) =>
  wrapper.get(`[data-testid="step-${id}"]`)

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  vi.mocked(districtsApi.listDistricts).mockResolvedValue([district('d1', 'Bezirk Nord'), district('d2', 'Bezirk Süd')])
  vi.mocked(districtsApi.listCongregations).mockResolvedValue([
    { id: 'c1', name: 'Nord', district_id: 'd1', service_times: [{ weekday: 6, time: '09:30' }] } as districtsApi.CongregationResponse,
  ])
  vi.mocked(leadersApi.listLeaders).mockResolvedValue([{ id: 'l1' } as leadersApi.LeaderResponse])
  vi.mocked(matrixApi.fetchMatrix).mockResolvedValue({
    dates: ['2026-11-01'],
    rows: [{
      congregation_id: 'c1',
      congregation_name: 'Nord',
      cells: { '2026-11-01': { event_id: 'e1', category: 'Gottesdienst', is_gap: true, approval_status: 'PLANNED' } as matrixApi.MatrixCell },
    }],
    holidays: {},
  })
  vi.mocked(exportTokensApi.listExportTokens).mockResolvedValue([])
})

describe('GettingStartedView', () => {
  it('shows the status of each step for the selected district and highlights the next one', async () => {
    const { wrapper } = await mountView()

    expect(wrapper.text()).toContain('Bezirk Nord')
    expect(step(wrapper, 'district').attributes('data-state')).toBe('done')
    expect(step(wrapper, 'congregations').attributes('data-state')).toBe('done')
    expect(step(wrapper, 'drafts').text()).toContain('1 Gottesdienst in den nächsten 4 Wochen geplant.')
    const assign = step(wrapper, 'assign')
    expect(assign.attributes('aria-current')).toBe('step')
    expect(assign.text()).toContain('1 Lücke')
    expect(assign.get('a').attributes('href')).toBe('/matrix')
    expect(step(wrapper, 'subscribe').text()).toContain('Noch kein Kalender-Abo eingerichtet.')

    const [, from, to] = vi.mocked(matrixApi.fetchMatrix).mock.calls[0]
    expect((new Date(to).getTime() - new Date(from).getTime()) / 86_400_000).toBeCloseTo(28, 0)
    expect(exportTokensApi.listExportTokens).toHaveBeenCalledWith('d1')
  })

  it('congratulates once everything is set up', async () => {
    vi.mocked(matrixApi.fetchMatrix).mockResolvedValue({
      dates: ['2026-11-01'],
      rows: [{
        congregation_id: 'c1',
        congregation_name: 'Nord',
        cells: { '2026-11-01': { event_id: 'e1', category: 'Gottesdienst', is_gap: false, approval_status: 'CONFIRMED' } as matrixApi.MatrixCell },
      }],
      holidays: {},
    })
    vi.mocked(exportTokensApi.listExportTokens).mockResolvedValue([
      { id: 't1', district_id: 'd1' } as exportTokensApi.ExportTokenResponse,
      { id: 't2', district_id: 'd2' } as exportTokensApi.ExportTokenResponse,
    ])
    const { wrapper } = await mountView()
    expect(wrapper.find('[data-testid="getting-started-done"]').exists()).toBe(true)
    expect(step(wrapper, 'subscribe').text()).toContain('1 Kalender-Abo eingerichtet.')
  })

  it('leaves admin steps to the district admin and does not ask a planner for tokens', async () => {
    const { wrapper } = await mountView('PLANNER')
    expect(exportTokensApi.listExportTokens).not.toHaveBeenCalled()
    expect(step(wrapper, 'subscribe').attributes('data-state')).toBe('unknown')
    expect(step(wrapper, 'leaders').find('a').exists()).toBe(false)
    expect(step(wrapper, 'drafts').find('a').exists()).toBe(true)
  })

  it('marks a step unknown when its request fails and keeps the others', async () => {
    vi.mocked(leadersApi.listLeaders).mockRejectedValue(new ApiError(500, 'Server Error', null))
    const { wrapper } = await mountView()
    expect(step(wrapper, 'leaders').text()).toContain('Amtsträger konnten nicht geladen werden.')
    expect(step(wrapper, 'drafts').attributes('data-state')).toBe('done')
  })

  it('shows the shared alert when the districts cannot be loaded', async () => {
    vi.mocked(districtsApi.listDistricts).mockRejectedValue(new ApiError(500, 'Server Error', null))
    const { wrapper } = await mountView()
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="getting-started-steps"]').exists()).toBe(false)
  })

  it('starts an installation without districts at the first step', async () => {
    vi.mocked(districtsApi.listDistricts).mockResolvedValue([])
    const { wrapper } = await mountView()
    expect(step(wrapper, 'district').attributes('aria-current')).toBe('step')
    expect(districtsApi.listCongregations).not.toHaveBeenCalled()
  })

  it('reloads the status when another district is selected', async () => {
    const { wrapper } = await mountView()
    useDistrictsStore().setSelectedDistrict('d2')
    await flushPromises()
    expect(districtsApi.listCongregations).toHaveBeenLastCalledWith('d2')
    expect(wrapper.text()).toContain('Bezirk Süd')
  })

  it('sends users who do not plan on to the event list', async () => {
    const { router } = await mountView('VIEWER')
    expect(router.currentRoute.value.name).toBe('events')
    expect(districtsApi.listDistricts).not.toHaveBeenCalled()
  })
})
