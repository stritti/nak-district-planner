// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

/**
 * Who may manage which membership. Mirrors
 * `app/domain/models/membership_policy.py`, which the API enforces; the UI uses
 * it only to offer units and roles the server will accept.
 */

import type { MembershipAccess } from '../api/auth'
import type { MembershipRole, ScopeType } from '../api/users'

export const ROLE_LABELS: Record<MembershipRole, string> = {
  DISTRICT_ADMIN: 'Bezirksadmin',
  CONGREGATION_ADMIN: 'Gemeindeadmin',
  PLANNER: 'Planer',
  VIEWER: 'Lesezugriff',
}

const RANK: Record<MembershipRole, number> = {
  VIEWER: 1,
  PLANNER: 2,
  CONGREGATION_ADMIN: 3,
  DISTRICT_ADMIN: 4,
}

/** DISTRICT_ADMIN only exists on districts, CONGREGATION_ADMIN only on congregations. */
export const ROLES_BY_SCOPE: Record<ScopeType, MembershipRole[]> = {
  DISTRICT: ['DISTRICT_ADMIN', 'PLANNER', 'VIEWER'],
  CONGREGATION: ['CONGREGATION_ADMIN', 'PLANNER', 'VIEWER'],
}

const ADMIN_ROLE: Record<ScopeType, MembershipRole> = {
  DISTRICT: 'DISTRICT_ADMIN',
  CONGREGATION: 'CONGREGATION_ADMIN',
}

function rank(role: string): number {
  return RANK[role as MembershipRole] ?? 0
}

export interface Unit {
  scopeType: ScopeType
  scopeId: string
  /** The district itself, or the congregation's district. */
  districtId: string
}

/** The highest role the actor may grant or remove in the unit, or null. */
export function managementLevel(
  memberships: MembershipAccess[],
  isSuperadmin: boolean,
  unit: Unit,
): MembershipRole | null {
  if (isSuperadmin) return 'DISTRICT_ADMIN'
  const roles = memberships
    .filter(
      (m) =>
        (m.scope_type === 'DISTRICT' && m.scope_id === unit.districtId) ||
        (unit.scopeType === 'CONGREGATION' &&
          m.scope_type === 'CONGREGATION' &&
          m.scope_id === unit.scopeId),
    )
    .map((m) => m.role)
  if (roles.length === 0) return null
  const level = roles.reduce((best, role) => (rank(role) > rank(best) ? role : best))
  return rank(level) >= rank(ADMIN_ROLE[unit.scopeType]) ? (level as MembershipRole) : null
}

/** True if every given role (new and existing) is at most the actor's level. */
export function mayManage(level: MembershipRole | null, ...roles: (MembershipRole | null)[]): boolean {
  return level !== null && roles.every((role) => role === null || rank(role) <= rank(level))
}

/** Roles the actor may assign in the unit. */
export function assignableRoles(level: MembershipRole | null, scopeType: ScopeType): MembershipRole[] {
  return ROLES_BY_SCOPE[scopeType].filter((role) => mayManage(level, role))
}

/** Whether the actor may open user administration at all. */
export function managesAnyUnit(memberships: MembershipAccess[], isSuperadmin: boolean): boolean {
  return isSuperadmin || memberships.some((m) => rank(m.role) >= rank('CONGREGATION_ADMIN'))
}
