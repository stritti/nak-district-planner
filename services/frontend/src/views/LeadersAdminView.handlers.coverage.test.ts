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

vi.mock('../api/districts', () => ({
  listDistricts: vi.fn(),
  listCongregations: vi.fn(),
  listGroups: vi.fn(),
}))
vi.mock('../api/leaders', () => ({
  LEADER_RANKS: [{ value: 'Pr.', label: 'Pr. – Priester' }],
  SPECIAL_ROLES: [{ value: 'Gemeindevorsteher', label: 'Gemeindevorsteher' }],
  leaderNameFromId: (id: string, values: Array<{ id: string; name: string }>) =>
    values.find((value) => value.id === id)?.name ?? '—',
  createLeader: vi.fn(),
  deleteLeader: vi.fn(),
  getSelfLeaderLink: vi.fn(),
  linkSelfToLeader: vi.fn(),
  listLeaders: vi.fn(),
  unlinkSelfFromLeader: vi.fn(),
  updateLeader: vi.fn(),
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
  congregation_id: 'c1',
  special_role: 'Gemeindevorsteher',
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

    await wrapper.get('button[title="Löschen"]').trigger('click')
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

    const deleteButtons = wrapper.findAll('button[title="Löschen"]')
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
