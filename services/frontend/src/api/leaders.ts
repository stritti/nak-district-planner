// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { apiFetch } from './client'

export const LEADER_RANKS = [
  { value: 'Di.',    label: 'Di. – Diakon' },
  { value: 'Pr.',    label: 'Pr. – Priester' },
  { value: 'Ev.',    label: 'Ev. – Evangelist' },
  { value: 'Hi.',    label: 'Hi. – Hirte' },
  { value: 'BE',     label: 'BE – Bezirksevangelist' },
  { value: 'BÄ',     label: 'BÄ – Bezirksältester' },
  { value: 'Bi.',    label: 'Bi. – Bischof' },
  { value: 'Ap.',    label: 'Ap. – Apostel' },
  { value: 'BezAp.', label: 'BezAp. – Bezirksapostel' },
  { value: 'StAp.',  label: 'StAp. – Stammapostel' },
] as const

export type LeaderRank = (typeof LEADER_RANKS)[number]['value']

export { SPECIAL_ROLES, type SpecialRole } from './leaderRoles'
import type { SpecialRole } from './leaderRoles'

export function leaderDisplayName(leader: LeaderResponse): string {
  return leader.rank ? `${leader.rank} ${leader.name}` : leader.name
}

export function leaderNameFromId(
  leaderId: string,
  leaders: LeaderResponse[],
): string {
  const leader = leaders.find((l) => l.id === leaderId)
  return leader ? leaderDisplayName(leader) : '—'
}

/** One service of a person: a congregation (`null` = district level) with an optional role. */
export interface LeaderAssignment {
  id: string
  congregation_id: string | null
  role: SpecialRole | null
  is_home: boolean
  revision: string
}

export interface LeaderAssignmentCreate {
  congregation_id: string | null
  role?: SpecialRole | null
  is_home?: boolean
}

export interface LeaderResponse {
  id: string
  name: string
  district_id: string
  rank: LeaderRank | null
  /** Home assignment first. */
  assignments: LeaderAssignment[]
  user_sub: string | null
  email: string | null
  phone: string | null
  notes: string | null
  hidden_from_lists?: boolean
  service_end_date?: string | null
  is_active: boolean
  created_at: string
  updated_at: string
  revision?: string
}

export interface LeaderSelfLinkResponse {
  linked: boolean
  leader: LeaderResponse | null
}

export interface LeaderCreate {
  name: string
  rank: LeaderRank
  /** Omitted: one district-level home assignment. Exactly one entry is the home. */
  assignments?: LeaderAssignmentCreate[]
  email?: string | null
  phone?: string | null
  notes?: string | null
  hidden_from_lists?: boolean
  service_end_date?: string | null
  is_active?: boolean
  /** Set after the user confirmed that a same-named person is a different one. */
  confirm_duplicate?: boolean
}

export interface LeaderUpdate {
  name?: string
  rank?: LeaderRank | null
  email?: string | null
  phone?: string | null
  notes?: string | null
  hidden_from_lists?: boolean
  service_end_date?: string | null
  is_active?: boolean
}

export function listLeaders(districtId: string, includeInactive = false): Promise<LeaderResponse[]> {
  return apiFetch<LeaderResponse[]>(`/api/v1/districts/${districtId}/leaders${includeInactive ? '?include_inactive=true' : ''}`)
}

export function createLeader(districtId: string, body: LeaderCreate): Promise<LeaderResponse> {
  return apiFetch<LeaderResponse>(`/api/v1/districts/${districtId}/leaders`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function updateLeader(
  districtId: string,
  leaderId: string,
  body: LeaderUpdate,
  revision: string,
): Promise<LeaderResponse> {
  if (!revision) return Promise.reject(new Error('Versionsinformation fehlt. Bitte neu laden.'))
  return apiFetch<LeaderResponse>(`/api/v1/districts/${districtId}/leaders/${leaderId}`, {
    method: 'PATCH',
    headers: { 'If-Match': revision },
    body: JSON.stringify(body),
  })
}

/** Scoped scalar edits require the original server-issued strong revision. */
export function updateLeaderInline(
  districtId: string,
  leaderId: string,
  body: Pick<LeaderUpdate, 'name' | 'email' | 'phone' | 'rank' | 'is_active'> & {
    /** Required by the server to deactivate; set only after the user confirmed. */
    confirm_deactivation?: boolean
  },
  revision: string,
): Promise<LeaderResponse> {
  if (!revision) return Promise.reject(new Error('Versionsinformation fehlt. Bitte neu laden.'))
  return apiFetch<LeaderResponse>(`/api/v1/districts/${districtId}/leaders/${leaderId}/inline`, {
    method: 'PATCH',
    headers: { 'If-Match': revision },
    body: JSON.stringify(body),
  })
}

function assignmentsUrl(districtId: string, leaderId: string): string {
  return `/api/v1/districts/${districtId}/leaders/${leaderId}/assignments`
}

export function addLeaderAssignment(
  districtId: string,
  leaderId: string,
  body: LeaderAssignmentCreate,
): Promise<LeaderAssignment> {
  return apiFetch<LeaderAssignment>(assignmentsUrl(districtId, leaderId), {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

/** Change the role, or make this the home assignment (`is_home: true` only). */
export function updateLeaderAssignment(
  districtId: string,
  leaderId: string,
  assignmentId: string,
  body: { role?: SpecialRole | null; is_home?: true },
  revision: string,
): Promise<LeaderAssignment> {
  if (!revision) return Promise.reject(new Error('Versionsinformation fehlt. Bitte neu laden.'))
  return apiFetch<LeaderAssignment>(`${assignmentsUrl(districtId, leaderId)}/${assignmentId}`, {
    method: 'PATCH',
    headers: { 'If-Match': revision },
    body: JSON.stringify(body),
  })
}

export function removeLeaderAssignment(
  districtId: string,
  leaderId: string,
  assignmentId: string,
  revision: string,
): Promise<void> {
  if (!revision) return Promise.reject(new Error('Versionsinformation fehlt. Bitte neu laden.'))
  return apiFetch<void>(`${assignmentsUrl(districtId, leaderId)}/${assignmentId}`, {
    method: 'DELETE',
    headers: { 'If-Match': revision },
  })
}

export function deleteLeader(districtId: string, leaderId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/districts/${districtId}/leaders/${leaderId}`, {
    method: 'DELETE',
  })
}

export function getSelfLeaderLink(districtId: string): Promise<LeaderSelfLinkResponse> {
  return apiFetch<LeaderSelfLinkResponse>(`/api/v1/districts/${districtId}/leaders/link-self`)
}

export function linkSelfToLeader(districtId: string, leaderId: string): Promise<LeaderSelfLinkResponse> {
  return apiFetch<LeaderSelfLinkResponse>(`/api/v1/districts/${districtId}/leaders/link-self`, {
    method: 'POST',
    body: JSON.stringify({ leader_id: leaderId }),
  })
}

export function unlinkSelfFromLeader(districtId: string): Promise<LeaderSelfLinkResponse> {
  return apiFetch<LeaderSelfLinkResponse>(`/api/v1/districts/${districtId}/leaders/link-self`, {
    method: 'DELETE',
  })
}

export function isLeaderEligibleOn(leader: LeaderResponse, localDate?: string): boolean {
  return leader.is_active && !leader.hidden_from_lists &&
    (!localDate || !leader.service_end_date || localDate <= leader.service_end_date)
}
