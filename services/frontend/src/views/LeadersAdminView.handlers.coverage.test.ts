// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import * as districtsApi from '../api/districts'
import * as leadersApi from '../api/leaders'
import * as registrationsApi from '../api/registrations'
import * as exportTokensApi from '../api/exportTokens'
import type { LeaderUnavailabilityResponse } from '../api/leaderUnavailabilities'
import { useAuthStore } from '../stores/auth'
import { useDistrictsStore } from '../stores/districts'
import { useLeaderUnavailabilitiesStore } from '../stores/leaderUnavailabilities'
import LeadersAdminView from './LeadersAdminView.vue'
import { ApiError } from '../api/errors'

const confirmMock = vi.hoisted(() => vi.fn())

vi.mock('../api/districts', () => ({
  listDistricts: vi.fn(),
  listCongregations: vi.fn(),
  listGroups: vi.fn(),
}))
vi.mock('../composables/useConfirm', () => ({ useConfirm: () => confirmMock }))
vi.mock('../api/leaders', () => ({
  LEADER_RANKS: [
    { value: 'Pr.', label: 'Pr. – Priester' },
    { value: 'Ev.', label: 'Ev. – Evangelist' },
    { value: 'Bi.', label: 'Bi. – Bischof' },
  ],
  SPECIAL_ROLES: [{ value: 'Gemeindevorsteher', label: 'Gemeindevorsteher' }],
  leaderDisplayName: (value: { rank: string | null; name: string }) => `${value.rank ?? ''} ${value.name}`.trim(),
  leaderNameFromId: (id: string, values: Array<{ id: string; name: string }>) =>
    values.find((value) => value.id === id)?.name ?? '—',
  addLeaderAssignment: vi.fn(),
  createLeader: vi.fn(),
  deleteLeader: vi.fn(),
  removeLeaderAssignment: vi.fn(),
  updateLeaderAssignment: vi.fn(),
  getSelfLeaderLink: vi.fn(),
  linkSelfToLeader: vi.fn(),
  listLeaders: vi.fn(),
  unlinkSelfFromLeader: vi.fn(),
  updateLeader: vi.fn(),
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
const leader: leadersApi.LeaderResponse = {
  id: 'l1',
  name: 'Anna Beispiel',
  district_id: 'd1',
  rank: 'Pr.',
  assignments: [
    { id: 'a1', congregation_id: 'c1', role: 'Gemeindevorsteher', is_home: true, revision: '"a1"' },
  ],
  user_sub: null,
  email: 'anna@example.org',
  phone: '123',
  notes: null,
  is_active: true,
  created_at: now,
  updated_at: now,
}
const registration: registrationsApi.RegistrationResponse = {
  id: 'r1',
  district_id: 'd1',
  name: 'Neue Person',
  email: 'neu@example.org',
  rank: 'Pr.',
  congregation_id: 'c1',
  special_role: null,
  phone: null,
  notes: null,
  status: 'PENDING',
  rejection_reason: null,
  user_sub: null,
  assigned_role: null,
  assigned_scope_type: null,
  assigned_scope_id: null,
  approved_by_sub: null,
  approved_at: null,
  idp_provision_status: null,
  idp_provision_error: null,
  idp_provisioned_at: null,
  created_at: now,
  updated_at: now,
}
const unavailability: LeaderUnavailabilityResponse = {
  id: 'u1',
  leader_id: 'l1',
  start_at: '2026-10-10T00:00:00Z',
  end_at: '2026-10-11T00:00:00Z',
  reason: 'URLAUB',
  note: null,
  created_at: now,
  updated_at: now,
}

const ConfirmDialogStub = defineComponent({
  name: 'ConfirmDialog',
  props: { open: Boolean },
  emits: ['confirm', 'cancel'],
  setup(props, { emit }) {
    return () => props.open
      ? h('div', { 'data-testid': 'confirm-dialog' }, [
          h('button', { 'data-testid': 'confirm-dialog-confirm', onClick: () => emit('confirm') }, 'confirm'),
          h('button', { 'data-testid': 'confirm-dialog-cancel', onClick: () => emit('cancel') }, 'cancel'),
        ])
      : null
  },
})

const UnavailabilityFormStub = defineComponent({
  name: 'LeaderUnavailabilityForm',
  setup(_, { expose }) {
    expose({ reset: vi.fn() })
    return () => h('div')
  },
})

function buttonByText(wrapper: VueWrapper, text: string) {
  const button = wrapper.findAll('button').find((candidate) => candidate.text().trim() === text)
  if (!button) throw new Error(`Button not found: ${text}`)
  return button
}

function modalByTitle(wrapper: VueWrapper, title: string) {
  const modal = wrapper.findAll('.modal-backdrop').find((candidate) => candidate.text().includes(title))
  if (!modal) throw new Error(`Modal not found: ${title}`)
  return modal
}

function registrationDialogByTitle(wrapper: VueWrapper, title: string) {
  const dialog = wrapper
    .findAll('div.fixed.inset-0')
    .find((candidate) => candidate.text().includes(title))
  if (!dialog) throw new Error(`Registration dialog not found: ${title}`)
  return dialog
}

async function mountView() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const districtsStore = useDistrictsStore()
  const authStore = useAuthStore()
  const unavailabilitiesStore = useLeaderUnavailabilitiesStore()
  districtsStore.districts = [{ id: 'd1', name: 'Bezirk Eins' }] as typeof districtsStore.districts
  districtsStore.selectedDistrictId = 'd1'
  authStore.isSuperadmin = true
  vi.spyOn(districtsStore, 'fetchDistricts').mockResolvedValue(undefined)
  vi.spyOn(unavailabilitiesStore, 'fetchUnavailabilities').mockResolvedValue(undefined)

  const wrapper = mount(LeadersAdminView, {
    global: {
      plugins: [pinia],
      stubs: {
        ConfirmDialog: ConfirmDialogStub,
        CopyButton: true,
        EmptyState: true,
        LeaderUnavailabilityForm: UnavailabilityFormStub,
        LeaderUnavailabilityList: true,
      },
    },
  })
  await flushPromises()
  return { wrapper, unavailabilitiesStore }
}

beforeEach(() => {
  vi.clearAllMocks()
  confirmMock.mockResolvedValue(true)
  vi.mocked(leadersApi.listLeaders).mockResolvedValue([leader])
  vi.mocked(districtsApi.listCongregations).mockResolvedValue([
    {
      id: 'c1',
      district_id: 'd1',
      name: 'Gemeinde Eins',
      group_id: null,
      group_name: null,
      service_times: [],
      created_at: now,
      updated_at: now,
    },
  ])
  vi.mocked(leadersApi.getSelfLeaderLink).mockResolvedValue({ linked: false, leader: null })
  vi.mocked(registrationsApi.listRegistrations).mockResolvedValue([registration])
  vi.mocked(leadersApi.deleteLeader).mockResolvedValue(undefined)
  vi.mocked(registrationsApi.deleteRegistration).mockResolvedValue(undefined)
  vi.mocked(exportTokensApi.createExportToken).mockResolvedValue({
    id: 'token-id',
    label: 'Pr. Anna Beispiel',
    token: 'token',
    token_type: 'INTERNAL',
    district_id: 'd1',
    congregation_id: null,
    leader_id: 'l1',
    is_active: true,
    created_at: now,
    updated_at: now,
  })
})

describe('LeadersAdminView rendered handlers', () => {
  it('executes native and component event handlers across all tabs and dialogs', async () => {
    const { wrapper, unavailabilitiesStore } = await mountView()

    await wrapper.get('select.form-select').setValue('d1')
    await flushPromises()

    const add = wrapper.findAll('button').find((candidate) => candidate.text().includes('Hinzufügen'))
    expect(add).toBeDefined()
    await add!.trigger('click')
    await modalByTitle(wrapper, 'Amtstragende:n hinzufügen').get('button.modal-close').trigger('click')

    await wrapper.get('button[title="Bearbeiten"]').trigger('click')
    await modalByTitle(wrapper, 'Amtstragende:n bearbeiten').get('button.modal-close').trigger('click')

    await wrapper.get('button[title="ICS-Export-Token erstellen"]').trigger('click')
    await modalByTitle(wrapper, 'ICS-Export').get('button.modal-close').trigger('click')

    await wrapper.get('button[title="Deaktivieren und ausblenden"]').trigger('click')
    await wrapper.get('[data-testid="confirm-dialog-cancel"]').trigger('click')

    await wrapper.get('button[title="Abwesenheiten verwalten"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Erfasste Abwesenheiten')

    await buttonByText(wrapper, 'Amtstragende').trigger('click')
    await buttonByText(wrapper, 'Registrierungen').trigger('click')
    await flushPromises()

    await wrapper.get('button[title="Genehmigen"]').trigger('click')
    await buttonByText(wrapper, 'Abbrechen').trigger('click')

    await wrapper.get('button[title="Ablehnen"]').trigger('click')
    await buttonByText(wrapper, 'Abbrechen').trigger('click')

    await wrapper.get('button[title="Löschen"]').trigger('click')
    await wrapper.get('[data-testid="confirm-dialog-confirm"]').trigger('click')
    await flushPromises()
    expect(registrationsApi.deleteRegistration).toHaveBeenCalledWith('d1', 'r1')

    await wrapper.get('[data-testid="unavailability-tab"]').trigger('click')
    await flushPromises()
    expect(unavailabilitiesStore.fetchUnavailabilities).toHaveBeenCalledWith('d1')

    wrapper.unmount()
  })

  it('executes generated v-model, backdrop, duplicate action and cancel handlers', async () => {
    const { wrapper } = await mountView()

    const addButton = wrapper.findAll('button').find((candidate) => candidate.text().includes('Hinzufügen'))
    expect(addButton).toBeDefined()
    await addButton!.trigger('click')
    let modal = modalByTitle(wrapper, 'Amtstragende:n hinzufügen')
    const addInputs = modal.findAll('input')
    const addSelects = modal.findAll('select')
    await addInputs[0]!.setValue('Neue Person')
    await addSelects[0]!.setValue('Pr.')
    await addSelects[1]!.setValue('Gemeindevorsteher')
    await addInputs[1]!.setValue('neu@example.org')
    await addInputs[2]!.setValue('456')
    await modal.trigger('click')

    await addButton!.trigger('click')
    modal = modalByTitle(wrapper, 'Amtstragende:n hinzufügen')
    await buttonByText(modal as unknown as VueWrapper, 'Abbrechen').trigger('click')

    const editButtons = wrapper.findAll('button[title="Bearbeiten"]')
    expect(editButtons.length).toBeGreaterThanOrEqual(2)
    await editButtons[0]!.trigger('click')
    modal = modalByTitle(wrapper, 'Amtstragende:n bearbeiten')
    const editInputs = modal.findAll('input')
    const editSelects = modal.findAll('select')
    await editInputs[0]!.setValue('Bearbeitet')
    await editSelects[0]!.setValue('Pr.')
    await editSelects[1]!.setValue('Gemeindevorsteher')
    await editSelects[2]!.setValue('c1')
    await editInputs[1]!.setValue('edit@example.org')
    await editInputs[2]!.setValue('789')
    await modal.get('textarea').setValue('Notiz')
    await editInputs[3]!.setValue(false)
    await modal.trigger('click')

    await editButtons[1]!.trigger('click')
    modal = modalByTitle(wrapper, 'Amtstragende:n bearbeiten')
    const cancelEdit = modal.findAll('button').find((candidate) => candidate.text() === 'Abbrechen')
    expect(cancelEdit).toBeDefined()
    await cancelEdit!.trigger('click')

    const exportButtons = wrapper.findAll('button[title="ICS-Export-Token erstellen"]')
    expect(exportButtons.length).toBeGreaterThanOrEqual(2)
    await exportButtons[1]!.trigger('click')
    modal = modalByTitle(wrapper, 'ICS-Export')
    await modal.trigger('click')

    const deleteButtons = wrapper.findAll('button[title="Deaktivieren und ausblenden"]')
    expect(deleteButtons.length).toBeGreaterThanOrEqual(2)
    await deleteButtons[1]!.trigger('click')
    await wrapper.get('[data-testid="confirm-dialog-cancel"]').trigger('click')

    const unavailabilityButtons = wrapper.findAll('button[title="Abwesenheiten verwalten"]')
    expect(unavailabilityButtons.length).toBeGreaterThanOrEqual(2)
    await unavailabilityButtons[1]!.trigger('click')
    await flushPromises()
    await buttonByText(wrapper, 'Amtstragende').trigger('click')

    await buttonByText(wrapper, 'Registrierungen').trigger('click')
    await flushPromises()

    await wrapper.get('button[title="Genehmigen"]').trigger('click')
    let dialog = registrationDialogByTitle(wrapper, 'Registrierung genehmigen')
    const approveSelects = dialog.findAll('select')
    await approveSelects[0]!.setValue('DISTRICT_ADMIN')
    await approveSelects[1]!.setValue('CONGREGATION')
    await approveSelects[2]!.setValue('Pr.')
    await approveSelects[3]!.setValue('c1')
    await approveSelects[4]!.setValue('Gemeindevorsteher')
    await dialog.trigger('click')

    await wrapper.get('button[title="Genehmigen"]').trigger('click')
    dialog = registrationDialogByTitle(wrapper, 'Registrierung genehmigen')
    const approveCancel = dialog.findAll('button').find((candidate) => candidate.text() === 'Abbrechen')
    expect(approveCancel).toBeDefined()
    await approveCancel!.trigger('click')

    await wrapper.get('button[title="Ablehnen"]').trigger('click')
    dialog = registrationDialogByTitle(wrapper, 'Registrierung ablehnen')
    await dialog.get('textarea').setValue('Nicht passend')
    await dialog.trigger('click')

    await wrapper.get('button[title="Ablehnen"]').trigger('click')
    dialog = registrationDialogByTitle(wrapper, 'Registrierung ablehnen')
    const rejectCancel = dialog.findAll('button').find((candidate) => candidate.text() === 'Abbrechen')
    expect(rejectCancel).toBeDefined()
    await rejectCancel!.trigger('click')

    await wrapper.get('button[title="Löschen"]').trigger('click')
    await wrapper.get('[data-testid="confirm-dialog-cancel"]').trigger('click')

    await buttonByText(wrapper, 'Amtstragende').trigger('click')
    const setupState = wrapper.vm.$.setupState as {
      pendingDeleteUnavailability: LeaderUnavailabilityResponse | null
    }
    setupState.pendingDeleteUnavailability = unavailability
    await wrapper.vm.$nextTick()
    await wrapper.get('[data-testid="confirm-dialog-cancel"]').trigger('click')
    expect(setupState.pendingDeleteUnavailability).toBeNull()

    wrapper.unmount()
  })
})

describe('LeadersAdminView inline contact editing', () => {
  it('persists leader name with the original revision and refreshes the listing', async () => {
    const versioned = { ...leader, revision: '"v1"' }
    vi.mocked(leadersApi.listLeaders).mockResolvedValue([versioned])
    vi.mocked(leadersApi.updateLeaderInline).mockResolvedValue({ ...versioned, name: 'Neu', revision: '"v2"' })
    const { wrapper } = await mountView()
    const initialFetches = vi.mocked(leadersApi.listLeaders).mock.calls.length
    const cell = wrapper.get('[data-inline-cell-id="leader-name-desktop-l1"]')
    await cell.trigger('click')
    await flushPromises()
    await cell.get('input').setValue('Neu')
    await cell.get('input').trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(leadersApi.updateLeaderInline).toHaveBeenCalledWith('d1', 'l1', { name: 'Neu' }, '"v1"')
    expect(leadersApi.listLeaders).toHaveBeenCalledTimes(initialFetches + 1)
  })

  it('renders legacy rows without a revision as read-only', async () => {
    const { wrapper } = await mountView()
    const cell = wrapper.get('[data-inline-cell-id="leader-email-desktop-l1"]')
    await cell.trigger('click')
    expect(cell.find('input').exists()).toBe(false)
    expect(leadersApi.updateLeaderInline).not.toHaveBeenCalled()
  })

  it('does not permit inline changes without planner membership', async () => {
    const versioned = { ...leader, revision: '"v1"' }
    vi.mocked(leadersApi.listLeaders).mockResolvedValue([versioned])
    const { wrapper } = await mountView()
    const auth = useAuthStore()
    auth.isSuperadmin = false
    auth.memberships = []
    await flushPromises()
    const cell = wrapper.get('[data-inline-cell-id="leader-phone-desktop-l1"]')
    await cell.trigger('click')
    expect(cell.find('input').exists()).toBe(false)
  })
})


async function narrowTo(role: 'PLANNER' | 'DISTRICT_ADMIN') {
  const auth = useAuthStore()
  auth.isSuperadmin = false
  auth.memberships = [{ role, scope_type: 'DISTRICT', scope_id: 'd1' }] as typeof auth.memberships
  await flushPromises()
}

async function edit(
  wrapper: VueWrapper,
  id: string,
  control: 'input' | 'select',
  value: string,
) {
  const cell = wrapper.get(`[data-inline-cell-id="${id}"]`)
  await cell.trigger('click')
  await flushPromises()
  await cell.get(control).setValue(value)
  await cell.get(control).trigger('keydown', { key: 'Enter' })
  await flushPromises()
  return cell
}

// District-level leader: appears in the "Bezirksebene" section, where only the district role fits.
const versionedLeader = {
  ...leader,
  assignments: [{ id: 'a1', congregation_id: null, role: null, is_home: true, revision: '"a1"' }],
  revision: '"v1"',
}

describe.each(['desktop', 'mobile'] as const)('LeadersAdminView inline appointment fields (%s)', (layout) => {
  beforeEach(() => {
    vi.mocked(leadersApi.listLeaders).mockResolvedValue([versionedLeader])
    vi.mocked(leadersApi.updateLeaderInline).mockResolvedValue({ ...versionedLeader, revision: '"v2"' })
    vi.mocked(districtsApi.listCongregations).mockResolvedValue(['c1', 'c2'].map((id) => ({
      id, district_id: 'd1', name: `Gemeinde ${id}`, group_id: null, group_name: null, service_times: [], created_at: now, updated_at: now,
    })))
  })

  it('saves rank with the captured revision', async () => {
    const wrapper = (await mountView()).wrapper
    await edit(wrapper, `leader-rank-${layout}-l1`, 'select', 'Bi.')
    expect(leadersApi.updateLeaderInline).toHaveBeenCalledWith('d1', 'l1', { rank: 'Bi.' }, '"v1"')
    expect(confirmMock).not.toHaveBeenCalled()
  })

  it('saves the role on the assignment of its section with that assignment\'s revision', async () => {
    vi.mocked(leadersApi.updateLeaderAssignment).mockResolvedValue(versionedLeader.assignments[0] as never)
    const wrapper = (await mountView()).wrapper
    await edit(wrapper, `leader-special_role-${layout}-l1`, 'select', 'Bezirksvorsteher')
    expect(leadersApi.updateLeaderAssignment).toHaveBeenCalledWith(
      'd1', 'l1', 'a1', { role: 'Bezirksvorsteher' }, '"a1"',
    )
    expect(leadersApi.updateLeaderInline).not.toHaveBeenCalled()
  })

  it('offers only the roles that fit the district level', async () => {
    const wrapper = (await mountView()).wrapper
    const cell = wrapper.get(`[data-inline-cell-id="leader-special_role-${layout}-l1"]`)
    await cell.trigger('click')
    await flushPromises()
    expect(cell.findAll('option').map((option) => option.text())).toEqual(['Keine', 'Bezirksvorsteher'])
  })

  it('does not allow clearing the grade', async () => {
    const wrapper = (await mountView()).wrapper
    const cell = await edit(wrapper, `leader-rank-${layout}-l1`, 'select', '')
    expect(cell.get('[role=alert]').text()).toContain('nicht leer')
    expect(leadersApi.updateLeaderInline).not.toHaveBeenCalled()
  })

  it('asks before deactivating and keeps the draft when declined', async () => {
    confirmMock.mockResolvedValue(false)
    const wrapper = (await mountView()).wrapper
    const cell = await edit(wrapper, `leader-is_active-${layout}-l1`, 'select', 'false')
    expect(confirmMock).toHaveBeenCalledWith(expect.objectContaining({ variant: 'danger' }))
    expect(leadersApi.updateLeaderInline).not.toHaveBeenCalled()
    expect(cell.get('[role=alert]').text()).toContain('abgebrochen')
  })

  it('deactivates after confirmation and reactivates without a prompt', async () => {
    const wrapper = (await mountView()).wrapper
    await edit(wrapper, `leader-is_active-${layout}-l1`, 'select', 'false')
    expect(leadersApi.updateLeaderInline).toHaveBeenLastCalledWith(
      'd1', 'l1', { is_active: false, confirm_deactivation: true }, '"v1"',
    )
    confirmMock.mockClear()
    vi.mocked(leadersApi.listLeaders).mockResolvedValue([{ ...leader, is_active: false, revision: '"v2"' }])
    const second = (await mountView()).wrapper
    await edit(second, `leader-is_active-${layout}-l1`, 'select', 'true')
    expect(leadersApi.updateLeaderInline).toHaveBeenLastCalledWith('d1', 'l1', { is_active: true }, '"v2"')
    expect(confirmMock).not.toHaveBeenCalled()
  })

  it('does not send the deactivation flag for reactivation or other fields', async () => {
    vi.mocked(leadersApi.listLeaders).mockResolvedValue([{ ...versionedLeader, is_active: false }])
    const { wrapper } = await mountView()
    await edit(wrapper, `leader-is_active-${layout}-l1`, 'select', 'true')
    expect(leadersApi.updateLeaderInline).toHaveBeenLastCalledWith('d1', 'l1', { is_active: true }, '"v1"')
  })

  it('recovers from a stale revision of an inactive leader instead of reporting it as removed', async () => {
    const inactive = { ...versionedLeader, is_active: false }
    // Mirrors the API: inactive leaders are only returned when include_inactive is requested.
    vi.mocked(leadersApi.listLeaders).mockImplementation(async (_district, includeInactive) =>
      includeInactive ? [inactive] : [])
    vi.mocked(leadersApi.updateLeaderInline).mockRejectedValue(
      new ApiError(412, 'Precondition Failed', { detail: 'Datensatz wurde zwischenzeitlich geändert.' }),
    )
    const { wrapper } = await mountView()
    const cell = await edit(wrapper, `leader-rank-${layout}-l1`, 'select', 'Bi.')
    vi.mocked(leadersApi.listLeaders).mockImplementation(async (_district, includeInactive) =>
      includeInactive ? [{ ...inactive, rank: 'Ev.', revision: '"v9"' }] : [])
    await cell.get('button').trigger('click')
    await vi.waitFor(() => expect(cell.get('[role=alert]').text()).toContain('Aktueller Stand geladen'))
    expect(cell.text()).not.toContain('entfernt')
    expect(leadersApi.listLeaders).toHaveBeenLastCalledWith('d1', true)
  })

  it('keeps activity read-only for planners but lets them edit the grade', async () => {
    const { wrapper } = await mountView()
    await narrowTo('PLANNER')
    const activity = wrapper.get(`[data-inline-cell-id="leader-is_active-${layout}-l1"]`)
    await activity.trigger('click')
    expect(activity.find('select').exists()).toBe(false)
    const rank = wrapper.get(`[data-inline-cell-id="leader-rank-${layout}-l1"]`)
    await rank.trigger('click')
    expect(rank.find('select').exists()).toBe(true)
  })

  it('shows the server message and offers a reload after a stale revision', async () => {
    vi.mocked(leadersApi.updateLeaderInline).mockRejectedValue(
      new ApiError(412, 'Precondition Failed', { detail: 'Datensatz wurde zwischenzeitlich geändert.' }),
    )
    const wrapper = (await mountView()).wrapper
    const cell = await edit(wrapper, `leader-rank-${layout}-l1`, 'select', 'Bi.')
    expect(cell.get('[role=alert]').text()).toContain('zwischenzeitlich geändert')
    vi.mocked(leadersApi.listLeaders).mockResolvedValue([{ ...versionedLeader, rank: 'Ev.', revision: '"v9"' }])
    await cell.get('button').trigger('click')
    await vi.waitFor(() => expect(cell.get('[role=alert]').text()).toContain('Aktueller Stand geladen'))
  })
})

describe('LeadersAdminView table regressions', () => {
  beforeEach(() => {
    vi.mocked(leadersApi.listLeaders).mockResolvedValue([versionedLeader])
    vi.mocked(leadersApi.updateLeaderInline).mockResolvedValue({ ...versionedLeader, revision: '"v2"' })
  })

  const FIELDS = ['name', 'email', 'phone', 'rank', 'special_role', 'is_active'] as const

  it.each([['VIEWER'], [undefined]])('offers no inline editor to a user with role %s', async (role) => {
    const { wrapper } = await mountView()
    const auth = useAuthStore()
    auth.isSuperadmin = false
    auth.memberships = role ? [{ role, scope_type: 'DISTRICT', scope_id: 'd1' }] as never : []
    await flushPromises()
    for (const layout of ['desktop', 'mobile']) {
      for (const field of FIELDS) {
        const cell = wrapper.get(`[data-inline-cell-id="leader-${field}-${layout}-l1"]`)
        await cell.trigger('click')
        await cell.trigger('keydown', { key: 'F2' })
        expect(cell.find('input, select').exists()).toBe(false)
      }
    }
    expect(wrapper.findAll('[data-inline-editable="true"]')).toHaveLength(0)
    expect(leadersApi.updateLeaderInline).not.toHaveBeenCalled()
  })

  it('saves with Tab and continues in the next editable cell of the same row', async () => {
    const { wrapper } = await mountView()
    const name = wrapper.get('[data-inline-cell-id="leader-name-desktop-l1"]')
    await name.trigger('click')
    await flushPromises()
    await name.get('input').setValue('Neuer Name')
    await name.get('input').trigger('keydown', { key: 'Tab' })
    await flushPromises()
    expect(leadersApi.updateLeaderInline).toHaveBeenCalledWith('d1', 'l1', { name: 'Neuer Name' }, '"v1"')
    expect(wrapper.get('[data-inline-cell-id="leader-special_role-desktop-l1"]').find('select').exists()).toBe(true)
  })

  it('does not advance with Tab while the current cell cannot be saved', async () => {
    vi.mocked(leadersApi.updateLeaderInline).mockRejectedValue(
      new ApiError(409, 'Conflict', { detail: 'Konflikt' }),
    )
    const { wrapper } = await mountView()
    const name = wrapper.get('[data-inline-cell-id="leader-name-desktop-l1"]')
    await name.trigger('click')
    await flushPromises()
    await name.get('input').setValue('Neuer Name')
    await name.get('input').trigger('keydown', { key: 'Tab' })
    await flushPromises()
    expect(name.get('[role="alert"]').text()).toContain('Konflikt')
    expect(wrapper.get('[data-inline-cell-id="leader-special_role-desktop-l1"]').find('select').exists()).toBe(false)
  })

  it('retries the same draft and revision after a transport failure', async () => {
    vi.mocked(leadersApi.updateLeaderInline)
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce({ ...versionedLeader, name: 'Neu', revision: '"v2"' })
    const { wrapper } = await mountView()
    const name = wrapper.get('[data-inline-cell-id="leader-name-desktop-l1"]')
    await name.trigger('click')
    await flushPromises()
    await name.get('input').setValue('Neu')
    await name.get('input').trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(name.get('[role="alert"]').text()).toContain('offline')
    await name.get('input').trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(vi.mocked(leadersApi.updateLeaderInline).mock.calls.map((call) => [call[2], call[3]])).toEqual([
      [{ name: 'Neu' }, '"v1"'],
      [{ name: 'Neu' }, '"v1"'],
    ])
  })

  it('shows registrations as a read-only table whose actions only open dialogs', async () => {
    const { wrapper } = await mountView()
    await buttonByText(wrapper, 'Registrierungen').trigger('click')
    await flushPromises()
    const table = wrapper.get('[data-testid="registrations-table"]')
    expect(table.find('[data-inline-editable]').exists()).toBe(false)
    expect(table.find('[data-inline-cell-id]').exists()).toBe(false)
    expect(table.find('input, select, textarea').exists()).toBe(false)
    expect(table.get('thead').classes()).toContain('table-thead')
    expect(table.get('th').classes()).toContain('table-th')

    await table.get('button[title="Genehmigen"]').trigger('click')
    expect(registrationsApi.approveRegistration).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Registrierung genehmigen')
  })
})
