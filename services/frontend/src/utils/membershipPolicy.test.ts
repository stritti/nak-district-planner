// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, expect, it } from 'vitest'
import type { MembershipAccess } from '../api/auth'
import { assignableRoles, managementLevel, managesAnyUnit, mayManage } from './membershipPolicy'

const district = (id: string) => ({ scopeType: 'DISTRICT' as const, scopeId: id, districtId: id })
const congregation = (id: string, districtId = 'd1') => ({
  scopeType: 'CONGREGATION' as const,
  scopeId: id,
  districtId,
})
const m = (role: string, scope_type: 'DISTRICT' | 'CONGREGATION', scope_id: string): MembershipAccess => ({
  role,
  scope_type,
  scope_id,
})

describe('membership policy', () => {
  it('lets a superadmin manage every unit without memberships', () => {
    expect(managementLevel([], true, district('d2'))).toBe('DISTRICT_ADMIN')
    expect(managesAnyUnit([], true)).toBe(true)
  })

  it('lets a district admin manage the district and its congregations only', () => {
    const actor = [m('DISTRICT_ADMIN', 'DISTRICT', 'd1')]
    expect(managementLevel(actor, false, district('d1'))).toBe('DISTRICT_ADMIN')
    expect(managementLevel(actor, false, congregation('c1'))).toBe('DISTRICT_ADMIN')
    expect(managementLevel(actor, false, district('d2'))).toBeNull()
    expect(managementLevel(actor, false, congregation('c9', 'd2'))).toBeNull()
  })

  it('never lets a congregation admin touch district memberships', () => {
    const actor = [m('CONGREGATION_ADMIN', 'CONGREGATION', 'c1')]
    expect(managementLevel(actor, false, congregation('c1'))).toBe('CONGREGATION_ADMIN')
    expect(managementLevel(actor, false, congregation('c2'))).toBeNull()
    expect(managementLevel(actor, false, district('d1'))).toBeNull()
  })

  it('gives planners and viewers no administration', () => {
    const actor = [m('PLANNER', 'DISTRICT', 'd1'), m('VIEWER', 'CONGREGATION', 'c1')]
    expect(managementLevel(actor, false, congregation('c1'))).toBeNull()
    expect(managesAnyUnit(actor, false)).toBe(false)
  })

  it('caps new and existing roles at the actor level', () => {
    expect(mayManage('CONGREGATION_ADMIN', 'PLANNER', 'VIEWER')).toBe(true)
    expect(mayManage('CONGREGATION_ADMIN', 'PLANNER', 'DISTRICT_ADMIN')).toBe(false)
    expect(mayManage(null, 'VIEWER')).toBe(false)
  })

  it('offers only roles that fit the scope and the actor level', () => {
    expect(assignableRoles('DISTRICT_ADMIN', 'DISTRICT')).toEqual(['DISTRICT_ADMIN', 'PLANNER', 'VIEWER'])
    expect(assignableRoles('DISTRICT_ADMIN', 'CONGREGATION')).toEqual(['CONGREGATION_ADMIN', 'PLANNER', 'VIEWER'])
    expect(assignableRoles('CONGREGATION_ADMIN', 'CONGREGATION')).toEqual(['CONGREGATION_ADMIN', 'PLANNER', 'VIEWER'])
    expect(assignableRoles(null, 'DISTRICT')).toEqual([])
  })
})
