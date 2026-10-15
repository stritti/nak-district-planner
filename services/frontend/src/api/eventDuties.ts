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
  suggestion_id: string | null
  needs_review: boolean
  over_capacity: boolean
  quarantined: boolean
}

export interface DutySuggestion {
  id: string
  display_name: string
  hidden: boolean
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
    }
  | {
      duty_category_id: string
      linked_user_sub: string
      name?: never
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

export function saveDutyAssignment(
  district: string,
  slot: string,
  data: DutyIdentity,
  id?: string,
): Promise<DutyAssignment> {
  return apiFetch(
    id
      ? `${base(district)}/assignments/${encodeURIComponent(id)}`
      : `${base(district)}/slots/${encodeURIComponent(slot)}`,
    { method: id ? 'PATCH' : 'POST', body: JSON.stringify(data) },
  )
}

export function revalidateDutyAssignment(
  district: string,
  id: string,
): Promise<DutyAssignment> {
  return apiFetch(
    `${base(district)}/assignments/${encodeURIComponent(id)}/revalidate`,
    { method: 'POST' },
  )
}

export function deleteDutyAssignment(district: string, id: string): Promise<void> {
  return apiFetch(`${base(district)}/assignments/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  })
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
): Promise<DutySuggestion> {
  return apiFetch(`${base(district)}/suggestions/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify({ hidden }),
  })
}
