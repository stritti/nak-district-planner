import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import * as districtsApi from '../api/districts'
import * as leadersApi from '../api/leaders'
import * as registrationsApi from '../api/registrations'
import * as exportTokensApi from '../api/exportTokens'
import type {
  LeaderUnavailabilityCreate,
  LeaderUnavailabilityResponse,
} from '../api/leaderUnavailabilities'
import { useAuthStore } from '../stores/auth'
import { useDistrictsStore } from '../stores/districts'
import { useLeaderUnavailabilitiesStore } from '../stores/leaderUnavailabilities'
import { useToastStore } from '../stores/toast'
import LeadersAdminView from './LeadersAdminView.vue'

vi.mock('../api/districts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/districts')>()
  return { ...actual, listCongregations: vi.fn() }
})
vi.mock('../api/leaders', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/leaders')>()
  return {
    ...actual,
    createLeader: vi.fn(),
    deleteLeader: vi.fn(),
    getSelfLeaderLink: vi.fn(),
    linkSelfToLeader: vi.fn(),
    listLeaders: vi.fn(),
    unlinkSelfFromLeader: vi.fn(),
    updateLeader: vi.fn(),
  }
})
vi.mock('../api/registrations', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/registrations')>()
  return {
    ...actual,
    approveRegistration: vi.fn(),
    deleteRegistration: vi.fn(),
    listRegistrations: vi.fn(),
    rejectRegistration: vi.fn(),
  }
})
vi.mock('../api/exportTokens', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/exportTokens')>()
  return { ...actual, createExportToken: vi.fn() }
})

const now = '2026-10-06T08:00:00Z'

function leader(
  id: string,
  name: string,
  overrides: Partial<leadersApi.LeaderResponse> = {},
): leadersApi.LeaderResponse {
  return {
    id,
    name,
    district_id: 'd1',
    rank: 'Pr.',
    congregation_id: null,
    special_role: null,
    user_sub: null,
    email: null,
    phone: null,
    notes: null,
    is_active: true,
    created_at: now,
    updated_at: now,
    ...overrides,
  }
}

function registration(
  id: string,
  status: registrationsApi.RegistrationStatus = 'PENDING',
  overrides: Partial<registrationsApi.RegistrationResponse> = {},
): registrationsApi.RegistrationResponse {
  return {
    id,
    district_id: 'd1',
    name: `Registrierung ${id}`,
    email: `${id}@example.org`,
    rank: 'Di.',
    congregation_id: 'c1',
    special_role: null,
    phone: null,
    notes: null,
    status,
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
    ...overrides,
  }
}

const leaders = [
  leader('l1', 'Zeta', { rank: 'Di.', congregation_id: 'c1' }),
  leader('l2', 'Alpha', { rank: 'Pr.', special_role: 'Gemeindevorsteher' }),
  leader('l3', 'Beta', { rank: 'Pr.', is_active: false }),
]

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

interface LeadersBindings {
  activeTab: 'leaders' | 'registrations' | 'unavailabilities'
  selectedDistrictId: string
  registrations: registrationsApi.RegistrationResponse[]
  leaders: leadersApi.LeaderResponse[]
  selfSelectedLeaderId: string
  selfLinkError: string
  addModal: {
    open: boolean
    congregationId: string | null
    name: string
    rank: leadersApi.LeaderRank | ''
    special_role: leadersApi.SpecialRole | null
    email: string
    phone: string
    error: string
  }
  editModal: {
    open: boolean
    leaderId: string
    name: string
    rank: leadersApi.LeaderRank | ''
    congregation_id: string | null
    special_role: leadersApi.SpecialRole | null
    email: string
    phone: string
    notes: string
    is_active: boolean
    error: string
  }
  approveModal: {
    open: boolean
    registrationId: string
    name: string
    email: string
    role: 'DISTRICT_ADMIN' | 'CONGREGATION_ADMIN' | 'PLANNER' | 'VIEWER'
    scope_type: 'DISTRICT' | 'CONGREGATION'
    rank: string | null
    congregation_id: string | null
    special_role: string | null
    error: string
  }
  rejectModal: {
    open: boolean
    registrationId: string
    name: string
    reason: string
    error: string
  }
  exportModal: {
    open: boolean
    leaderId: string
    leaderName: string
    leaderRank: string
    icsUrl: string
    error: string
  }
  pendingDeleteReg: registrationsApi.RegistrationResponse | null
  pendingDeleteLeader: leadersApi.LeaderResponse | null
  pendingDeleteUnavailability: LeaderUnavailabilityResponse | null
  activeLeaderOptions: leadersApi.LeaderResponse[]
  canManageUnavailabilities: boolean
  leadersForSection: (congregationId: string | null) => leadersApi.LeaderResponse[]
  congregationName: (id: string | null) => string
  loadRegistrations: () => Promise<void>
  switchToRegistrations: () => Promise<void>
  switchToUnavailabilities: (leaderId?: string) => Promise<void>
  openUnavailabilitiesFor: (value: leadersApi.LeaderResponse) => void
  saveUnavailability: (body: LeaderUnavailabilityCreate) => Promise<void>
  confirmDeleteUnavailability: (value: LeaderUnavailabilityResponse) => void
  executeDeleteUnavailability: () => Promise<void>
  openApproveModal: (value: registrationsApi.RegistrationResponse) => void
  doApprove: () => Promise<void>
  openRejectModal: (value: registrationsApi.RegistrationResponse) => void
  doReject: () => Promise<void>
  confirmDeleteReg: (value: registrationsApi.RegistrationResponse) => void
  executeDeleteReg: () => Promise<void>
  onDistrictChange: () => Promise<void>
  loadSelfLink: () => Promise<void>
  connectSelfLink: () => Promise<void>
  removeSelfLink: () => Promise<void>
  openAddModal: (congregationId: string | null) => void
  saveAdd: () => Promise<void>
  openEditModal: (value: leadersApi.LeaderResponse) => void
  saveEdit: () => Promise<void>
  confirmDelete: (value: leadersApi.LeaderResponse) => void
  executeDeleteLeader: () => Promise<void>
  openExportModal: (value: leadersApi.LeaderResponse) => void
  createExportToken: () => Promise<void>
}

function setup() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const authStore = useAuthStore()
  const districtsStore = useDistrictsStore()
  const unavailabilitiesStore = useLeaderUnavailabilitiesStore()
  const toastStore = useToastStore()

  districtsStore.districts = [{ id: 'd1', name: 'Bezirk Eins' }] as typeof districtsStore.districts
  districtsStore.selectedDistrictId = 'd1'
  vi.spyOn(districtsStore, 'fetchDistricts').mockResolvedValue(undefined)
  vi.spyOn(unavailabilitiesStore, 'fetchUnavailabilities').mockResolvedValue(undefined)
  vi.spyOn(unavailabilitiesStore, 'addUnavailability').mockResolvedValue(unavailability)
  vi.spyOn(unavailabilitiesStore, 'removeUnavailability').mockResolvedValue(undefined)

  authStore.isSuperadmin = true

  const wrapper = mount(LeadersAdminView, {
    global: {
      plugins: [pinia],
      stubs: {
        ConfirmDialog: true,
        CopyButton: true,
        EmptyState: true,
        LeaderUnavailabilityForm: true,
        LeaderUnavailabilityList: true,
      },
    },
  })
  const vm = wrapper.vm.$.setupState as LeadersBindings
  return { wrapper, vm, authStore, districtsStore, unavailabilitiesStore, toastStore }
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(leadersApi.listLeaders).mockResolvedValue(leaders)
  vi.mocked(districtsApi.listCongregations).mockResolvedValue([
    { id: 'c1', district_id: 'd1', name: 'Gemeinde Eins', group_id: null, group_name: null, service_times: [], created_at: now, updated_at: now },
  ])
  vi.mocked(leadersApi.getSelfLeaderLink).mockResolvedValue({ linked: true, leader: leaders[0] })
  vi.mocked(registrationsApi.listRegistrations).mockResolvedValue([
    registration('r1'),
    registration('r2', 'APPROVED', { idp_provision_status: 'FAILED', idp_provision_error: 'IDP kaputt' }),
    registration('r3', 'REJECTED', { rank: null, congregation_id: null }),
  ])
  vi.mocked(leadersApi.createLeader).mockResolvedValue(leader('l4', 'Neu'))
  vi.mocked(leadersApi.updateLeader).mockImplementation(async (_district, id, body) => ({
    ...leader(id, 'Aktualisiert'),
    ...body,
  } as leadersApi.LeaderResponse))
  vi.mocked(leadersApi.deleteLeader).mockResolvedValue(undefined)
  vi.mocked(leadersApi.linkSelfToLeader).mockResolvedValue({ linked: true, leader: leaders[1] })
  vi.mocked(leadersApi.unlinkSelfFromLeader).mockResolvedValue({ linked: false, leader: null })
  vi.mocked(registrationsApi.approveRegistration).mockImplementation(async (_district, id) => registration(id, 'APPROVED'))
  vi.mocked(registrationsApi.rejectRegistration).mockImplementation(async (_district, id) => registration(id, 'REJECTED'))
  vi.mocked(registrationsApi.deleteRegistration).mockResolvedValue(undefined)
  vi.mocked(exportTokensApi.createExportToken).mockResolvedValue({
    id: 't1',
    label: 'Pr. Test',
    token: 'secret-token',
    token_type: 'INTERNAL',
    district_id: 'd1',
    congregation_id: null,
    leader_id: 'l1',
    is_active: true,
    created_at: now,
    updated_at: now,
  })
})

describe('LeadersAdminView coverage gaps', () => {
  it('loads, sorts and exercises registration workflows', async () => {
    const { wrapper, vm, toastStore } = setup()
    const success = vi.spyOn(toastStore, 'success')
    await flushPromises()

    expect(vm.leadersForSection(null).map((value) => value.id)).toEqual(['l2', 'l3'])
    expect(vm.leadersForSection('c1').map((value) => value.id)).toEqual(['l1'])
    expect(vm.congregationName('c1')).toBe('Gemeinde Eins')
    expect(vm.congregationName(null)).toBe('')
    expect(vm.congregationName('missing')).toBe('')
    expect(vm.activeLeaderOptions.map((value) => value.name)).toEqual(['Alpha', 'Zeta'])

    await vm.switchToRegistrations()
    await flushPromises()
    expect(vm.activeTab).toBe('registrations')
    expect(vm.registrations).toHaveLength(3)
    expect(wrapper.text()).toContain('Registrierung r1')
    expect(wrapper.text()).toContain('IDP kaputt')

    vm.openApproveModal(vm.registrations[0])
    vm.approveModal.scope_type = 'CONGREGATION'
    vm.approveModal.congregation_id = null
    await vm.doApprove()
    expect(vm.approveModal.error).toContain('Gemeinde ausgewählt')

    vm.approveModal.scope_type = 'DISTRICT'
    await vm.doApprove()
    await flushPromises()
    expect(registrationsApi.approveRegistration).toHaveBeenCalledWith(
      'd1',
      'r1',
      expect.objectContaining({ scope_type: 'DISTRICT', scope_id: 'd1' }),
    )
    expect(vm.approveModal.open).toBe(false)

    const rejected = registration('reject-me')
    vm.registrations = [...vm.registrations, rejected]
    vm.openRejectModal(rejected)
    vm.rejectModal.reason = ' Nicht passend '
    await vm.doReject()
    expect(registrationsApi.rejectRegistration).toHaveBeenCalledWith('d1', 'reject-me', {
      reason: ' Nicht passend ',
    })
    expect(success).toHaveBeenCalledWith('Registrierung abgelehnt', rejected.name)

    const doomed = registration('delete-me')
    vm.registrations = [...vm.registrations, doomed]
    vm.confirmDeleteReg(doomed)
    await vm.executeDeleteReg()
    expect(registrationsApi.deleteRegistration).toHaveBeenCalledWith('d1', 'delete-me')
    expect(vm.registrations.some((value) => value.id === 'delete-me')).toBe(false)
  })

  it('exercises leader create, edit, delete and export workflows', async () => {
    const { vm, toastStore } = setup()
    const success = vi.spyOn(toastStore, 'success')
    await flushPromises()

    vm.openAddModal('c1')
    vm.addModal.name = ' Neue Person '
    vm.addModal.rank = 'Di.'
    vm.addModal.special_role = 'Gemeindevorsteher'
    vm.addModal.email = ' person@example.org '
    vm.addModal.phone = ' 123 '
    await vm.saveAdd()
    expect(leadersApi.createLeader).toHaveBeenCalledWith('d1', {
      name: 'Neue Person',
      rank: 'Di.',
      congregation_id: 'c1',
      special_role: 'Gemeindevorsteher',
      email: 'person@example.org',
      phone: '123',
    })
    expect(success).toHaveBeenCalledWith('Amtsträger:in erstellt', 'Neu')

    vm.openEditModal(leaders[0])
    vm.editModal.name = ' Bearbeitet '
    vm.editModal.rank = 'Pr.'
    vm.editModal.email = ' edit@example.org '
    vm.editModal.phone = ' '
    vm.editModal.notes = ' Notiz '
    vm.editModal.is_active = false
    await vm.saveEdit()
    expect(leadersApi.updateLeader).toHaveBeenCalledWith('d1', 'l1', expect.objectContaining({
      name: 'Bearbeitet',
      rank: 'Pr.',
      email: 'edit@example.org',
      phone: null,
      notes: 'Notiz',
      is_active: false,
    }))

    vm.confirmDelete(vm.leaders[0])
    const deletedId = vm.pendingDeleteLeader?.id
    await vm.executeDeleteLeader()
    expect(leadersApi.deleteLeader).toHaveBeenCalledWith('d1', deletedId)
    expect(vm.leaders.some((value) => value.id === deletedId)).toBe(false)

    vm.openExportModal(leaders[1])
    await vm.createExportToken()
    expect(exportTokensApi.createExportToken).toHaveBeenCalledWith(expect.objectContaining({
      label: 'Pr. Alpha',
      district_id: 'd1',
      leader_id: 'l2',
    }))
    expect(vm.exportModal.icsUrl).toContain('/api/v1/export/secret-token/calendar.ics')
  })

  it('exercises unavailability and self-link workflows', async () => {
    const { vm, unavailabilitiesStore, toastStore, authStore } = setup()
    const success = vi.spyOn(toastStore, 'success')
    await flushPromises()

    await vm.switchToUnavailabilities('l1')
    expect(vm.activeTab).toBe('unavailabilities')
    expect(unavailabilitiesStore.fetchUnavailabilities).toHaveBeenCalledWith('d1')

    vm.openUnavailabilitiesFor(leaders[1])
    await flushPromises()
    expect(unavailabilitiesStore.fetchUnavailabilities).toHaveBeenCalledWith('d1')

    const body: LeaderUnavailabilityCreate = {
      leader_id: 'l1',
      start_at: unavailability.start_at,
      end_at: unavailability.end_at,
      reason: 'URLAUB',
      note: null,
    }
    await vm.saveUnavailability(body)
    expect(unavailabilitiesStore.addUnavailability).toHaveBeenCalledWith(body)
    expect(success).toHaveBeenCalledWith(
      'Abwesenheit erfasst',
      expect.stringContaining('Di. Zeta'),
    )

    vm.confirmDeleteUnavailability(unavailability)
    await vm.executeDeleteUnavailability()
    expect(unavailabilitiesStore.removeUnavailability).toHaveBeenCalledWith('u1')
    expect(success).toHaveBeenCalledWith('Abwesenheit gelöscht', expect.any(String))

    vm.selfSelectedLeaderId = 'l2'
    await vm.connectSelfLink()
    expect(leadersApi.linkSelfToLeader).toHaveBeenCalledWith('d1', 'l2')
    await vm.removeSelfLink()
    expect(leadersApi.unlinkSelfFromLeader).toHaveBeenCalledWith('d1')

    authStore.isSuperadmin = false
    authStore.memberships = []
    expect(vm.canManageUnavailabilities).toBe(false)
    vi.mocked(unavailabilitiesStore.addUnavailability).mockClear()
    await vm.saveUnavailability(body)
    expect(unavailabilitiesStore.addUnavailability).not.toHaveBeenCalled()
  })

  it('covers empty-district guards and provider failures', async () => {
    const { vm, unavailabilitiesStore, toastStore, authStore } = setup()
    const errorToast = vi.spyOn(toastStore, 'error')
    await flushPromises()

    vi.mocked(registrationsApi.listRegistrations).mockRejectedValueOnce(new Error('Registrierungen kaputt'))
    await expect(vm.loadRegistrations()).rejects.toThrow('Registrierungen kaputt')

    vi.mocked(unavailabilitiesStore.fetchUnavailabilities).mockRejectedValueOnce(new Error('Abwesenheiten kaputt'))
    await vm.switchToUnavailabilities()
    expect(errorToast).toHaveBeenCalledWith('Abwesenheiten konnten nicht geladen werden', 'Abwesenheiten kaputt')

    vi.mocked(leadersApi.getSelfLeaderLink).mockRejectedValueOnce(new Error('Link kaputt'))
    await vm.loadSelfLink()
    expect(vm.selfLinkError).toBe('Link kaputt')

    vm.selfSelectedLeaderId = 'l2'
    vi.mocked(leadersApi.linkSelfToLeader).mockRejectedValueOnce(new Error('Verbinden kaputt'))
    await vm.connectSelfLink()
    expect(vm.selfLinkError).toBe('Verbinden kaputt')

    vi.mocked(leadersApi.unlinkSelfFromLeader).mockRejectedValueOnce(new Error('Lösen kaputt'))
    await vm.removeSelfLink()
    expect(vm.selfLinkError).toBe('Lösen kaputt')

    vm.openAddModal(null)
    vm.addModal.name = 'Fehler'
    vm.addModal.rank = 'Di.'
    vi.mocked(leadersApi.createLeader).mockRejectedValueOnce(new Error('Create kaputt'))
    await vm.saveAdd()
    expect(vm.addModal.error).toBe('Create kaputt')

    vm.openEditModal(leaders[0])
    vi.mocked(leadersApi.updateLeader).mockRejectedValueOnce(new Error('Update kaputt'))
    await vm.saveEdit()
    expect(vm.editModal.error).toBe('Update kaputt')

    vm.confirmDelete(leaders[0])
    vi.mocked(leadersApi.deleteLeader).mockRejectedValueOnce(new Error('Delete kaputt'))
    await vm.executeDeleteLeader()
    expect(errorToast).toHaveBeenCalledWith('Löschen fehlgeschlagen', 'Delete kaputt')

    vm.openExportModal(leaders[0])
    vi.mocked(exportTokensApi.createExportToken).mockRejectedValueOnce(new Error('Export kaputt'))
    await vm.createExportToken()
    expect(vm.exportModal.error).toBe('Export kaputt')

    vm.registrations = [registration('bad-approve')]
    vm.openApproveModal(vm.registrations[0])
    vi.mocked(registrationsApi.approveRegistration).mockRejectedValueOnce(new Error('Approve kaputt'))
    await vm.doApprove()
    expect(vm.approveModal.error).toBe('Approve kaputt')

    vm.openRejectModal(vm.registrations[0])
    vi.mocked(registrationsApi.rejectRegistration).mockRejectedValueOnce(new Error('Reject kaputt'))
    await vm.doReject()
    expect(vm.rejectModal.error).toBe('Reject kaputt')

    vm.confirmDeleteReg(vm.registrations[0])
    vi.mocked(registrationsApi.deleteRegistration).mockRejectedValueOnce(new Error('Registration delete kaputt'))
    await vm.executeDeleteReg()
    expect(errorToast).toHaveBeenCalledWith('Löschen fehlgeschlagen', 'Registration delete kaputt')

    vi.mocked(unavailabilitiesStore.addUnavailability).mockRejectedValueOnce(new Error('Abwesenheit create kaputt'))
    await vm.saveUnavailability({
      leader_id: 'l1',
      start_at: unavailability.start_at,
      end_at: unavailability.end_at,
      reason: 'URLAUB',
      note: null,
    })
    expect(errorToast).toHaveBeenCalledWith('Abwesenheit konnte nicht erfasst werden', 'Abwesenheit create kaputt')

    vm.confirmDeleteUnavailability(unavailability)
    vi.mocked(unavailabilitiesStore.removeUnavailability).mockRejectedValueOnce(new Error('Abwesenheit delete kaputt'))
    await vm.executeDeleteUnavailability()
    expect(errorToast).toHaveBeenCalledWith('Löschen fehlgeschlagen', 'Abwesenheit delete kaputt')

    authStore.isSuperadmin = false
    authStore.memberships = [{
      role: 'PLANNER',
      scope_type: 'DISTRICT',
      scope_id: 'd1',
    }]
    expect(vm.canManageUnavailabilities).toBe(true)

    vm.selectedDistrictId = ''
    await vm.onDistrictChange()
    expect(vm.leaders).toEqual([])
    vm.selfSelectedLeaderId = 'l1'
    await vm.connectSelfLink()
    expect(leadersApi.linkSelfToLeader).not.toHaveBeenLastCalledWith('', 'l1')
    await vm.removeSelfLink()
    await vm.createExportToken()
  })
})
