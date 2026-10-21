// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import * as districtsApi from '../api/districts'
import * as leadersApi from '../api/leaders'
import * as registrationsApi from '../api/registrations'
import { ApiError } from '../api/errors'
import { useAuthStore } from '../stores/auth'
import { useDistrictsStore } from '../stores/districts'
import { useLeaderUnavailabilitiesStore } from '../stores/leaderUnavailabilities'
import LeadersAdminView from './LeadersAdminView.vue'

vi.mock('../api/districts', () => ({
  listDistricts: vi.fn(),
  listCongregations: vi.fn(),
  listGroups: vi.fn(),
}))
vi.mock('../api/leaders', () => ({
  LEADER_RANKS: [{ value: 'Pr.', label: 'Pr. – Priester' }],
  SPECIAL_ROLES: [
    { value: 'Gemeindevorsteher', label: 'Gemeindevorsteher' },
    { value: 'Bezirksvorsteher', label: 'Bezirksvorsteher' },
  ],
  leaderDisplayName: (value: { rank: string | null; name: string }) => `${value.rank ?? ''} ${value.name}`.trim(),
  leaderNameFromId: () => '—',
  addLeaderAssignment: vi.fn(),
  createLeader: vi.fn(),
  deleteLeader: vi.fn(),
  getSelfLeaderLink: vi.fn(),
  linkSelfToLeader: vi.fn(),
  listLeaders: vi.fn(),
  removeLeaderAssignment: vi.fn(),
  unlinkSelfFromLeader: vi.fn(),
  updateLeader: vi.fn(),
  updateLeaderAssignment: vi.fn(),
  updateLeaderInline: vi.fn(),
}))
vi.mock('../api/registrations', () => ({
  approveRegistration: vi.fn(),
  deleteRegistration: vi.fn(),
  listRegistrations: vi.fn(),
  rejectRegistration: vi.fn(),
}))
vi.mock('../api/exportTokens', () => ({ createExportToken: vi.fn() }))

const now = '2026-10-06T08:00:00Z'
const congregation = (id: string) => ({
  id, district_id: 'd1', name: `Gemeinde ${id}`, group_id: null, group_name: null, service_times: [],
  created_at: now, updated_at: now,
})
const assignment = (
  id: string, congregation_id: string | null, is_home = false, role: leadersApi.SpecialRole | null = null,
): leadersApi.LeaderAssignment => ({ id, congregation_id, role, is_home, revision: `"${id}"` })

// Hans serves c1 (home) and c2 (as congregation leader there).
const hans = (assignments: leadersApi.LeaderAssignment[]): leadersApi.LeaderResponse => ({
  id: 'l1', name: 'Hans Muster', district_id: 'd1', rank: 'Pr.', assignments, user_sub: null,
  email: null, phone: null, notes: null, is_active: true, created_at: now, updated_at: now, revision: '"v1"',
})
const twoCongregations = () => hans([assignment('a1', 'c1', true), assignment('a2', 'c2', false, 'Gemeindevorsteher')])

async function mountView() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const districtsStore = useDistrictsStore()
  const auth = useAuthStore()
  const unavailabilities = useLeaderUnavailabilitiesStore()
  districtsStore.districts = [{ id: 'd1', name: 'Bezirk Eins' }] as typeof districtsStore.districts
  districtsStore.selectedDistrictId = 'd1'
  auth.isSuperadmin = true
  vi.spyOn(districtsStore, 'fetchDistricts').mockResolvedValue(undefined)
  vi.spyOn(unavailabilities, 'fetchUnavailabilities').mockResolvedValue(undefined)
  const wrapper = mount(LeadersAdminView, {
    global: {
      plugins: [pinia],
      stubs: { ConfirmDialog: true, CopyButton: true, EmptyState: true, LeaderUnavailabilityForm: true, LeaderUnavailabilityList: true },
    },
  })
  await flushPromises()
  return { wrapper, auth }
}

async function openEdit(wrapper: VueWrapper) {
  await wrapper.get('button[title="Bearbeiten"]').trigger('click')
  await flushPromises()
  return wrapper.get('[data-testid="assignments"]')
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(leadersApi.listLeaders).mockResolvedValue([twoCongregations()])
  vi.mocked(districtsApi.listCongregations).mockResolvedValue(['c1', 'c2', 'c3'].map(congregation))
  vi.mocked(leadersApi.getSelfLeaderLink).mockResolvedValue({ linked: false, leader: null })
  vi.mocked(registrationsApi.listRegistrations).mockResolvedValue([])
})

describe('a person with several assignments', () => {
  it('appears in every assigned section with the home highlighted', async () => {
    const { wrapper } = await mountView()
    const sections = wrapper.findAll('div.mb-8')
    const withPerson = sections.filter((section) => section.text().includes('Hans Muster'))
    expect(withPerson.map((section) => section.find('h2').text())).toEqual(['Gemeinde c1', 'Gemeinde c2'])
    const [home, other] = withPerson.map((section) => section.get('[data-testid="home-marker"]').text())
    expect(home).toBe('Heimat')
    expect(other).toBe('Heimat: Gemeinde c1')
  })

  it('has section-specific coordinator ids even for person-level columns', async () => {
    const { wrapper } = await mountView()
    const ids = wrapper.findAll('[data-inline-cell-id]').map((el) => el.attributes('data-inline-cell-id'))
    expect(new Set(ids).size).toBe(ids.length)
    expect(ids).toContain('leader-name-desktop-l1-c1')
    expect(ids).toContain('leader-name-desktop-l1-c2')
  })

  it('does not label an unseen home assignment as the first visible congregation', async () => {
    vi.mocked(leadersApi.listLeaders).mockResolvedValue([hans([
      assignment('a1', 'c1'), assignment('a2', 'c2'),
    ])])
    const { wrapper } = await mountView()
    expect(wrapper.text()).not.toContain('Heimat: Gemeinde c1')
    expect(wrapper.text()).toContain('Heimat nicht sichtbar')
  })

  it('shows the role held in each section', async () => {
    const { wrapper } = await mountView()
    const roleIn = (section: string) =>
      wrapper.findAll('div.mb-8').find((s) => s.find('h2').text() === section)!
         .get(`[data-inline-cell-id="leader-special_role-desktop-l1-${section.endsWith('c1') ? 'c1' : 'c2'}"]`).text()
    expect(roleIn('Gemeinde c1')).toBe('—')
    expect(roleIn('Gemeinde c2')).toBe('Gemeindevorsteher')
  })

  it('shows no home marker for a person with a single assignment', async () => {
    vi.mocked(leadersApi.listLeaders).mockResolvedValue([hans([assignment('a1', 'c1', true)])])
    const { wrapper } = await mountView()
    expect(wrapper.get('[data-testid="home-marker"]').text()).toBe('')
  })

  it('saves a role inline on the assignment of its own section', async () => {
    vi.mocked(leadersApi.updateLeaderAssignment).mockResolvedValue(assignment('a1', 'c1', true, 'Gemeindevorsteher'))
    const { wrapper } = await mountView()
    const cell = wrapper.findAll('div.mb-8').find((s) => s.find('h2').text() === 'Gemeinde c1')!
      .get('[data-inline-cell-id="leader-special_role-desktop-l1-c1"]')
    await cell.trigger('click')
    await flushPromises()
    await cell.get('select').setValue('Gemeindevorsteher')
    await cell.get('select').trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(leadersApi.updateLeaderAssignment).toHaveBeenCalledWith(
      'd1', 'l1', 'a1', { role: 'Gemeindevorsteher' }, '"a1"',
    )
  })

  it('reloads the stored role and its revision after a stale change', async () => {
    vi.mocked(leadersApi.updateLeaderAssignment).mockRejectedValue(new ApiError(412, 'Precondition Failed', { detail: 'alt' }))
    const { wrapper } = await mountView()
    const cell = wrapper.findAll('div.mb-8').find((s) => s.find('h2').text() === 'Gemeinde c2')!
      .get('[data-inline-cell-id="leader-special_role-desktop-l1-c2"]')
    await cell.trigger('click')
    await flushPromises()
    await cell.get('select').setValue('')
    await cell.get('select').trigger('keydown', { key: 'Enter' })
    await flushPromises()
    vi.mocked(leadersApi.listLeaders).mockResolvedValue([
      hans([assignment('a1', 'c1', true), assignment('a2', 'c2', false, null)]),
    ])
    await cell.get('button').trigger('click')
    await vi.waitFor(() => expect(cell.get('[role=alert]').text()).toContain('Aktueller Stand geladen'))
  })
})

describe('assignments in the edit dialog', () => {
  it('adds an assignment and shows the stored state afterwards', async () => {
    vi.mocked(leadersApi.addLeaderAssignment).mockResolvedValue(assignment('a3', 'c3'))
    const { wrapper } = await mountView()
    const box = await openEdit(wrapper)
    vi.mocked(leadersApi.listLeaders).mockResolvedValue([
      hans([assignment('a1', 'c1', true), assignment('a2', 'c2', false, 'Gemeindevorsteher'), assignment('a3', 'c3')]),
    ])
    await box.get('select[aria-label="Neue Zuordnung"]').setValue('c3')
    await box.findAll('button').find((b) => b.text() === 'Hinzufügen')!.trigger('click')
    await flushPromises()
    expect(leadersApi.addLeaderAssignment).toHaveBeenCalledWith('d1', 'l1', { congregation_id: 'c3', role: null })
    expect(wrapper.find('[data-testid="assignment-a3"]').exists()).toBe(true)
  })

  it('adds the district level as a null congregation', async () => {
    vi.mocked(leadersApi.addLeaderAssignment).mockResolvedValue(assignment('a3', null))
    const { wrapper } = await mountView()
    const box = await openEdit(wrapper)
    await box.get('select[aria-label="Neue Zuordnung"]').setValue('district')
    await box.findAll('button').find((b) => b.text() === 'Hinzufügen')!.trigger('click')
    await flushPromises()
    expect(leadersApi.addLeaderAssignment).toHaveBeenCalledWith('d1', 'l1', { congregation_id: null, role: null })
  })

  it('changes a role, moves the home and removes an assignment with that assignment\'s revision', async () => {
    vi.mocked(leadersApi.updateLeaderAssignment).mockResolvedValue(assignment('a2', 'c2'))
    vi.mocked(leadersApi.removeLeaderAssignment).mockResolvedValue(undefined)
    const { wrapper } = await mountView()
    const box = await openEdit(wrapper)
    const row = box.get('[data-testid="assignment-a2"]')
    await row.get('select').setValue('')
    await flushPromises()
    expect(leadersApi.updateLeaderAssignment).toHaveBeenLastCalledWith('d1', 'l1', 'a2', { role: null }, '"a2"')
    await row.findAll('button').find((b) => b.text() === 'Als Heimat festlegen')!.trigger('click')
    await flushPromises()
    expect(leadersApi.updateLeaderAssignment).toHaveBeenLastCalledWith('d1', 'l1', 'a2', { is_home: true }, '"a2"')
    await row.findAll('button').find((b) => b.text() === 'Entfernen')!.trigger('click')
    await flushPromises()
    expect(leadersApi.removeLeaderAssignment).toHaveBeenCalledWith('d1', 'l1', 'a2', '"a2"')
  })

  it('shows the server message and the stored state when a change is rejected', async () => {
    vi.mocked(leadersApi.removeLeaderAssignment).mockRejectedValue(
      new ApiError(409, 'Conflict', { detail: { message: 'Die Heimat-Zuordnung kann nicht entfernt werden.' } }),
    )
    const { wrapper } = await mountView()
    const box = await openEdit(wrapper)
    await box.get('[data-testid="assignment-a2"]').findAll('button').find((b) => b.text() === 'Entfernen')!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toMatch(/Fehler beim Ändern der Zuordnung|Conflict|Heimat-Zuordnung/)
    expect(leadersApi.listLeaders).toHaveBeenCalledTimes(2) // initial load and the refresh after the failure
  })

  it('lets a congregation planner change only the assignment of their congregation', async () => {
    const { wrapper, auth } = await mountView()
    auth.isSuperadmin = false
    auth.memberships = [{ role: 'PLANNER', scope_type: 'CONGREGATION', scope_id: 'c2' }] as typeof auth.memberships
    await flushPromises()
    const box = await openEdit(wrapper)
    expect(box.get('[data-testid="assignment-a1"] select').attributes('disabled')).toBeDefined()
    expect(box.get('[data-testid="assignment-a2"] select').attributes('disabled')).toBeUndefined()
  })

  it('lets a district planner manage every assignment', async () => {
    const { wrapper, auth } = await mountView()
    auth.isSuperadmin = false
    auth.memberships = [{ role: 'PLANNER', scope_type: 'DISTRICT', scope_id: 'd1' }] as typeof auth.memberships
    await flushPromises()
    const box = await openEdit(wrapper)
    expect(box.get('[data-testid="assignment-a1"] select').attributes('disabled')).toBeUndefined()
    expect(box.get('[data-testid="assignment-a2"] select').attributes('disabled')).toBeUndefined()
  })
})
