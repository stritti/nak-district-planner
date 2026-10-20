// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { apiFetch } from './client'

export interface DutyCategory {
  id: string
  district_id: string
  congregation_id: string | null
  code: string
  label: string
  event_categories: string[]
  enabled: boolean
  capacity: number
}

export interface DutyConfiguration {
  id: string
  duty_category_id: string
  congregation_id: string
  event_categories: string[]
  enabled: boolean
  capacity: number
}

export interface DutyAssignment {
  id: string
  planning_slot_id: string
  duty_category_id: string
  district_id: string
  congregation_id: string | null
  display_name: string
  duty_label: string
  linked_user_sub: string | null
  leader_id?: string | null
  suggestion_id: string | null
  needs_review: boolean
  over_capacity: boolean
  quarantined: boolean
  revision: string
}

export interface DutySuggestion {
  id: string
  display_name: string
  hidden: boolean
  revision: string
}

export interface EligibleUser {
  sub: string
  display_name: string
}

export type DutyIdentity =
  | {
      duty_category_id: string
      name: string
      suggestion_id?: string
      linked_user_sub?: never
      leader_id?: never
      confirm_warnings?: boolean
    }
  | {
      duty_category_id: string
      linked_user_sub: string
      name?: never
      leader_id?: never
      confirm_warnings?: boolean
    }
  | {
      duty_category_id: string
      leader_id: string
      name?: never
      linked_user_sub?: never
      confirm_warnings?: boolean
    }

const base = (district: string) =>
  `/api/v1/districts/${encodeURIComponent(district)}/duties`

const scope = (congregation?: string) =>
  congregation
    ? `?${new URLSearchParams({ congregation_id: congregation })}`
    : ''

export function listDutyCategories(
  district: string,
  congregation?: string,
): Promise<{ categories: DutyCategory[]; overrides: DutyConfiguration[] }> {
  return apiFetch(`${base(district)}/categories${scope(congregation)}`)
}

export function createDutyCategory(
  district: string,
  data: Omit<DutyCategory, 'id' | 'district_id'>,
): Promise<DutyCategory> {
  return apiFetch(`${base(district)}/categories`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateDutyCategory(
  district: string,
  id: string,
  data: Partial<DutyCategory>,
): Promise<DutyCategory> {
  return apiFetch(`${base(district)}/categories/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function putDutyConfiguration(
  district: string,
  data: Omit<DutyConfiguration, 'id'>,
): Promise<DutyConfiguration> {
  return apiFetch(`${base(district)}/configuration`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export function restoreDutyInheritance(
  district: string,
  id: string,
  congregation: string,
): Promise<void> {
  return apiFetch(
    `${base(district)}/configuration/${encodeURIComponent(id)}${scope(congregation)}`,
    { method: 'DELETE' },
  )
}

export function getSlotDuties(
  district: string,
  id: string,
  includeQuarantined = false,
): Promise<{ categories: DutyCategory[]; assignments: DutyAssignment[] }> {
  const query = includeQuarantined ? '?include_quarantined=true' : ''
  return apiFetch(`${base(district)}/slots/${encodeURIComponent(id)}${query}`)
}

const missingRevision = () =>
  Promise.reject(new Error('Versionsinformation fehlt. Bitte neu laden.'))

/** Creates an assignment, or replaces `id` conditionally on the `revision` it was read with. */
export function saveDutyAssignment(
  district: string,
  slot: string,
  data: DutyIdentity,
  id?: string,
  revision?: string,
): Promise<DutyAssignment> {
  if (!id) {
    return apiFetch(`${base(district)}/slots/${encodeURIComponent(slot)}`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }
  if (!revision) return missingRevision()
  return apiFetch(`${base(district)}/assignments/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: { 'If-Match': revision },
    body: JSON.stringify(data),
  })
}

export function revalidateDutyAssignment(
  district: string,
  id: string,
  revision: string,
): Promise<DutyAssignment> {
  if (!revision) return missingRevision()
  return apiFetch(
    `${base(district)}/assignments/${encodeURIComponent(id)}/revalidate`,
    { method: 'POST', headers: { 'If-Match': revision } },
  )
}

export function deleteDutyAssignment(
  district: string,
  id: string,
  revision: string,
): Promise<void> {
  if (!revision) return missingRevision()
  return apiFetch(`${base(district)}/assignments/${encodeURIComponent(id)}`, {
    method: 'DELETE',
    headers: { 'If-Match': revision },
  })
}

export interface DutyLeaderChoice {
  id: string
  name: string
  rank: string | null
}

/** Leaders a duty of this slot may reference: eligible on its date, for any slot planner. */
export function listLeaderChoices(district: string, slot: string): Promise<DutyLeaderChoice[]> {
  return apiFetch(`${base(district)}/slots/${encodeURIComponent(slot)}/leaders`)
}

export function listEligibleUsers(
  district: string,
  congregation?: string,
): Promise<EligibleUser[]> {
  return apiFetch(`${base(district)}/eligible-users${scope(congregation)}`)
}

export function listSuggestions(
  district: string,
  category: string,
  congregation?: string,
  hidden = false,
): Promise<DutySuggestion[]> {
  const query = new URLSearchParams({
    duty_category_id: category,
    include_hidden: String(hidden),
  })
  if (congregation) query.set('congregation_id', congregation)
  return apiFetch(`${base(district)}/suggestions?${query}`)
}

export function setSuggestionHidden(
  district: string,
  id: string,
  hidden: boolean,
  revision: string,
): Promise<DutySuggestion> {
  if (!revision) return missingRevision()
  return apiFetch(`${base(district)}/suggestions/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: { 'If-Match': revision },
    body: JSON.stringify({ hidden }),
  })
}
