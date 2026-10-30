// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { apiFetch } from './client'

export type ScopeType = 'DISTRICT' | 'CONGREGATION'
export type MembershipRole = 'DISTRICT_ADMIN' | 'CONGREGATION_ADMIN' | 'PLANNER' | 'VIEWER'

export interface AdminMembership {
  id: string
  role: MembershipRole
  scope_type: ScopeType
  scope_id: string
  scope_name: string | null
  /** The district itself, or the congregation's district. */
  district_id: string
}

export interface AdminUser {
  sub: string
  email: string
  username: string
  name: string | null
  /** Only reported to superadmins; null for other administrators. */
  is_superadmin: boolean | null
  /** Only the memberships the caller may manage. */
  memberships: AdminMembership[]
}

export interface MembershipAssign {
  scope_type: ScopeType
  scope_id: string
  role: MembershipRole
}

const base = '/api/v1/users'
const userPath = (sub: string) => `${base}/${encodeURIComponent(sub)}`

/** Users the caller may manage; 403 when the caller manages no unit. */
export function listUsers(): Promise<AdminUser[]> {
  return apiFetch<AdminUser[]>(base)
}

/** Assign a role in one unit; an existing membership of that unit is updated. */
export function assignMembership(sub: string, body: MembershipAssign): Promise<AdminUser> {
  return apiFetch<AdminUser>(`${userPath(sub)}/memberships`, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export function removeMembership(sub: string, membershipId: string): Promise<void> {
  return apiFetch<void>(`${userPath(sub)}/memberships/${membershipId}`, { method: 'DELETE' })
}

/** Superadmins only; 409 when the last superadmin would be revoked. */
export function setSuperadmin(sub: string, isSuperadmin: boolean): Promise<AdminUser> {
  return apiFetch<AdminUser>(`${userPath(sub)}/superadmin`, {
    method: 'PUT',
    body: JSON.stringify({ is_superadmin: isSuperadmin }),
  })
}
