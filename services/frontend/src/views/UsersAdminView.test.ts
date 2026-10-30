// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

const mocks = vi.hoisted(() => ({ confirm: vi.fn() }))

vi.mock('../api/districts')
vi.mock('../api/users')
vi.mock('../composables/useConfirm', () => ({ useConfirm: () => mocks.confirm }))

import * as districtApi from '../api/districts'
import * as usersApi from '../api/users'
import { ApiError } from '../api/errors'
import type { MembershipAccess } from '../api/auth'
import { useAuthStore } from '../stores/auth'
import { useToastStore } from '../stores/toast'
import UsersAdminView from './UsersAdminView.vue'

const stamp = { created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' }
const districts = [
  { id: 'd1', name: 'Tuttlingen', state_code: 'BW', ...stamp },
  { id: 'd2', name: 'Konstanz', state_code: 'BW', ...stamp },
]
const congregations: Record<string, districtApi.CongregationResponse[]> = {
  d1: [{ id: 'c1', name: 'Stockach', district_id: 'd1', group_id: null, service_times: [], ...stamp }],
  d2: [{ id: 'c2', name: 'Singen', district_id: 'd2', group_id: null, service_times: [], ...stamp }],
}

function adminUser(overrides: Partial<usersApi.AdminUser> = {}): usersApi.AdminUser {
  return {
    sub: 'sub-anna',
    email: 'anna@example.org',
    username: 'anna',
    name: 'Anna',
    is_superadmin: null,
    memberships: [
      { id: 'm1', role: 'VIEWER', scope_type: 'CONGREGATION', scope_id: 'c1', scope_name: 'Stockach', district_id: 'd1' },
    ],
    ...overrides,
  }
}

function mountView(access: { memberships?: MembershipAccess[]; superadmin?: boolean; sub?: string } = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const auth = useAuthStore()
  auth.memberships = access.memberships ?? [{ role: 'DISTRICT_ADMIN', scope_type: 'DISTRICT', scope_id: 'd1' }]
  auth.isSuperadmin = access.superadmin ?? false
  auth.user = { sub: access.sub ?? 'sub-me', email: 'me@example.org', name: 'Ich' } as never
  auth.refreshCurrentUserFlags = vi.fn().mockResolvedValue(undefined)
  const toast = useToastStore()
  vi.spyOn(toast, 'success')
  vi.spyOn(toast, 'error')
  return { wrapper: mount(UsersAdminView, { global: { plugins: [pinia] } }), auth, toast }
}

function optionTexts(wrapper: ReturnType<typeof mount>, label: string): string[] {
  return wrapper
    .get(`select[aria-label="${label}"]`)
    .findAll('option')
    .filter((option) => option.attributes('disabled') === undefined)
    .map((option) => option.text())
}

describe('UsersAdminView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.confirm.mockResolvedValue(true)
    vi.mocked(districtApi.listDistricts).mockResolvedValue(districts)
    vi.mocked(districtApi.listCongregations).mockImplementation(async (id) => congregations[id] ?? [])
    vi.mocked(usersApi.listUsers).mockResolvedValue([adminUser()])
    vi.mocked(usersApi.removeMembership).mockResolvedValue(undefined)
  })

  it('lists users with their memberships and the caller’s own access', async () => {
    const { wrapper } = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('Anna')
    expect(wrapper.text()).toContain('Lesezugriff · Stockach')
    expect(wrapper.text()).toContain('Bezirksadmin · Tuttlingen')
    expect(wrapper.text()).not.toContain('Zum Superadmin ernennen')
  })

  it('offers only manageable units and roles that fit the unit', async () => {
    const { wrapper } = mountView()
    await flushPromises()

    expect(optionTexts(wrapper, 'Einheit für anna@example.org')).toEqual(['Bezirk Tuttlingen', 'Gemeinde Stockach'])

    await wrapper.get('select[aria-label="Einheit für anna@example.org"]').setValue('CONGREGATION:c1')
    expect(optionTexts(wrapper, 'Rolle für anna@example.org')).toEqual(['Gemeindeadmin', 'Planer', 'Lesezugriff'])
  })

  it('never offers district units or a district role to a congregation admin', async () => {
    const { wrapper } = mountView({
      memberships: [{ role: 'CONGREGATION_ADMIN', scope_type: 'CONGREGATION', scope_id: 'c1' }],
    })
    await flushPromises()

    expect(optionTexts(wrapper, 'Einheit für anna@example.org')).toEqual(['Gemeinde Stockach'])
    await wrapper.get('select[aria-label="Einheit für anna@example.org"]').setValue('CONGREGATION:c1')
    expect(optionTexts(wrapper, 'Rolle für anna@example.org')).not.toContain('Bezirksadmin')
  })

  it('finds congregations a congregation admin manages without district access', async () => {
    vi.mocked(districtApi.listDistricts).mockResolvedValue([])
    vi.mocked(usersApi.listUsers).mockResolvedValue([
      adminUser(),
      adminUser({
        sub: 'sub-me',
        email: 'me@example.org',
        memberships: [
          { id: 'm5', role: 'CONGREGATION_ADMIN', scope_type: 'CONGREGATION', scope_id: 'c1', scope_name: 'Stockach', district_id: 'd1' },
        ],
      }),
    ])
    const { wrapper } = mountView({
      memberships: [{ role: 'CONGREGATION_ADMIN', scope_type: 'CONGREGATION', scope_id: 'c1' }],
    })
    await flushPromises()

    expect(optionTexts(wrapper, 'Einheit für anna@example.org')).toEqual(['Gemeinde Stockach'])
    expect(wrapper.text()).toContain('Gemeindeadmin · Stockach')
  })

  it('drops a role that no longer fits when the unit changes', async () => {
    const { wrapper } = mountView()
    await flushPromises()

    const unit = wrapper.get('select[aria-label="Einheit für anna@example.org"]')
    await unit.setValue('DISTRICT:d1')
    await wrapper.get('select[aria-label="Rolle für anna@example.org"]').setValue('DISTRICT_ADMIN')
    await unit.setValue('CONGREGATION:c1')

    expect((wrapper.get('select[aria-label="Rolle für anna@example.org"]').element as HTMLSelectElement).value).toBe('')
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()
    await wrapper.get('form').trigger('submit')
    expect(usersApi.assignMembership).not.toHaveBeenCalled()
  })

  it('keeps a role that still fits when the unit changes', async () => {
    const { wrapper } = mountView()
    await flushPromises()

    const unit = wrapper.get('select[aria-label="Einheit für anna@example.org"]')
    await unit.setValue('DISTRICT:d1')
    await wrapper.get('select[aria-label="Rolle für anna@example.org"]').setValue('PLANNER')
    await unit.setValue('CONGREGATION:c1')

    expect((wrapper.get('select[aria-label="Rolle für anna@example.org"]').element as HTMLSelectElement).value).toBe('PLANNER')
  })

  it('reloads the screen after removing an own membership', async () => {
    vi.mocked(usersApi.listUsers).mockResolvedValue([adminUser({ sub: 'sub-me' })])
    const { wrapper, auth } = mountView({ sub: 'sub-me' })
    await flushPromises()

    await wrapper.get('button[aria-label="Lesezugriff in Stockach entfernen"]').trigger('click')
    await flushPromises()

    expect(auth.refreshCurrentUserFlags).toHaveBeenCalledOnce()
    expect(usersApi.listUsers).toHaveBeenCalledTimes(2)
  })

  it('reloads the screen after changing an own membership', async () => {
    vi.mocked(usersApi.listUsers).mockResolvedValue([adminUser({ sub: 'sub-me', email: 'me@example.org' })])
    vi.mocked(usersApi.assignMembership).mockResolvedValue(adminUser({ sub: 'sub-me' }))
    const { wrapper, auth } = mountView({ sub: 'sub-me' })
    await flushPromises()

    await wrapper.get('select[aria-label="Einheit für me@example.org"]').setValue('DISTRICT:d1')
    await wrapper.get('select[aria-label="Rolle für me@example.org"]').setValue('VIEWER')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(auth.refreshCurrentUserFlags).toHaveBeenCalledOnce()
    expect(usersApi.listUsers).toHaveBeenCalledTimes(2)
  })

  it('assigns a role in another unit and keeps the existing membership', async () => {
    const updated = adminUser({
      memberships: [
        ...adminUser().memberships,
        { id: 'm2', role: 'PLANNER', scope_type: 'DISTRICT', scope_id: 'd1', scope_name: 'Tuttlingen', district_id: 'd1' },
      ],
    })
    vi.mocked(usersApi.assignMembership).mockResolvedValue(updated)
    const { wrapper, toast } = mountView()
    await flushPromises()

    await wrapper.get('select[aria-label="Einheit für anna@example.org"]').setValue('DISTRICT:d1')
    await wrapper.get('select[aria-label="Rolle für anna@example.org"]').setValue('PLANNER')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(usersApi.assignMembership).toHaveBeenCalledWith('sub-anna', {
      scope_type: 'DISTRICT',
      scope_id: 'd1',
      role: 'PLANNER',
    })
    expect(wrapper.text()).toContain('Lesezugriff · Stockach')
    expect(wrapper.text()).toContain('Planer · Tuttlingen')
    expect(toast.success).toHaveBeenCalled()
  })

  it('removes one membership after confirmation', async () => {
    const { wrapper } = mountView()
    await flushPromises()

    await wrapper.get('button[aria-label="Lesezugriff in Stockach entfernen"]').trigger('click')
    await flushPromises()

    expect(mocks.confirm).toHaveBeenCalledOnce()
    expect(usersApi.removeMembership).toHaveBeenCalledWith('sub-anna', 'm1')
    expect(wrapper.text()).toContain('Keine Zuordnungen in deinen Einheiten.')
  })

  it('keeps the membership when the removal is cancelled', async () => {
    mocks.confirm.mockResolvedValue(false)
    const { wrapper } = mountView()
    await flushPromises()

    await wrapper.get('button[aria-label="Lesezugriff in Stockach entfernen"]').trigger('click')
    await flushPromises()

    expect(usersApi.removeMembership).not.toHaveBeenCalled()
  })

  it('hides the remove button for a role above the caller', async () => {
    vi.mocked(usersApi.listUsers).mockResolvedValue([
      adminUser({
        memberships: [
          { id: 'm9', role: 'DISTRICT_ADMIN', scope_type: 'DISTRICT', scope_id: 'd1', scope_name: 'Tuttlingen', district_id: 'd1' },
        ],
      }),
    ])
    const { wrapper } = mountView({
      memberships: [{ role: 'CONGREGATION_ADMIN', scope_type: 'CONGREGATION', scope_id: 'c1' }],
    })
    await flushPromises()

    expect(wrapper.find('button[aria-label="Bezirksadmin in Tuttlingen entfernen"]').exists()).toBe(false)
  })

  it('lets a superadmin appoint another superadmin', async () => {
    vi.mocked(usersApi.listUsers).mockResolvedValue([adminUser({ is_superadmin: false })])
    vi.mocked(usersApi.setSuperadmin).mockResolvedValue(adminUser({ is_superadmin: true }))
    const { wrapper, auth } = mountView({ memberships: [], superadmin: true })
    await flushPromises()

    await wrapper.get('button.text-sm.px-3').trigger('click')
    await flushPromises()

    expect(usersApi.setSuperadmin).toHaveBeenCalledWith('sub-anna', true)
    expect(wrapper.text()).toContain('Superadmin entziehen')
    expect(auth.refreshCurrentUserFlags).not.toHaveBeenCalled()
  })

  it('shows the server reason when the last superadmin would be revoked', async () => {
    vi.mocked(usersApi.listUsers).mockResolvedValue([adminUser({ sub: 'sub-me', is_superadmin: true })])
    vi.mocked(usersApi.setSuperadmin).mockRejectedValue(
      new ApiError(409, 'Conflict', { detail: 'Der letzte Superadmin kann nicht entzogen werden.' }),
    )
    const { wrapper, toast } = mountView({ memberships: [], superadmin: true })
    await flushPromises()

    await wrapper.get('button.text-sm.px-3').trigger('click')
    await flushPromises()

    expect(toast.error).toHaveBeenCalledWith('Der letzte Superadmin kann nicht entzogen werden.')
    expect(wrapper.text()).toContain('Superadmin entziehen')
  })

  it('refreshes the own access after revoking the own superadmin status', async () => {
    vi.mocked(usersApi.listUsers).mockResolvedValue([adminUser({ sub: 'sub-me', is_superadmin: true })])
    vi.mocked(usersApi.setSuperadmin).mockResolvedValue(adminUser({ sub: 'sub-me', is_superadmin: false }))
    const { wrapper, auth } = mountView({ memberships: [], superadmin: true })
    await flushPromises()

    await wrapper.get('button.text-sm.px-3').trigger('click')
    await flushPromises()

    expect(usersApi.setSuperadmin).toHaveBeenCalledWith('sub-me', false)
    expect(auth.refreshCurrentUserFlags).toHaveBeenCalledOnce()
    expect(usersApi.listUsers).toHaveBeenCalledTimes(2)
  })

  it('explains a 403 instead of showing an empty list', async () => {
    vi.mocked(usersApi.listUsers).mockRejectedValue(new ApiError(403, 'Forbidden', { detail: 'Keine Benutzerverwaltung' }))
    const { wrapper } = mountView({ memberships: [{ role: 'PLANNER', scope_type: 'DISTRICT', scope_id: 'd1' }] })
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toBe('Du verwaltest keine Bezirke oder Gemeinden.')
  })

  it('filters users by name or email', async () => {
    vi.mocked(usersApi.listUsers).mockResolvedValue([
      adminUser(),
      adminUser({ sub: 'sub-ben', email: 'ben@example.org', username: 'ben', name: 'Ben' }),
    ])
    const { wrapper } = mountView()
    await flushPromises()

    await wrapper.get('input[type="search"]').setValue('ben@')
    expect(wrapper.find('[data-testid="user-sub-anna"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="user-sub-ben"]').exists()).toBe(true)
  })
})
