// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { apiFetch } from './client'

export type RecurrenceKind = 'WEEKLY' | 'MONTHLY_DAY' | 'MONTHLY_WEEKDAY'
export type ChecklistStatus = 'OPEN' | 'ACCEPTED' | 'SKIPPED' | 'CONFLICT' | 'NEEDS_REVIEW'

export interface RecurrenceRule {
  kind: RecurrenceKind
  anchor_date: string
  interval: number
  weekdays: number[]
  day_of_month: number | null
  weekday: number | null
  ordinal: number | null
  version: number
}

export interface RecurringTemplateInput {
  title: string
  description: string | null
  category: string
  congregation_id: string | null
  start_time: string
  duration_minutes: number
  recurrence: RecurrenceRule
  applicability: string[]
  excluded_dates: string[]
  active_from: string | null
  active_until: string | null
  is_active: boolean
}

export interface RecurringTemplate extends RecurringTemplateInput {
  id: string
  district_id: string
  revision: number
  timezone: string
}

export interface RecurringTemplateList {
  items: RecurringTemplate[]
  total: number
  limit?: number
  offset?: number
}

export interface ChecklistItem {
  template_id: string
  district_id: string
  congregation_id: string | null
  title: string
  description: string | null
  category: string
  occurrence_local_date: string
  start_time: string
  duration_minutes: number
  template_revision: number
  status: ChecklistStatus
  decision_status: 'ACCEPTED' | 'SKIPPED' | null
  planning_slot_id: string | null
  reason: string | null
}

export interface ChecklistPage {
  items: ChecklistItem[]
  total: number
  limit: number
  offset: number
  counts: Record<ChecklistStatus, number>
}

export interface ChecklistFilters {
  year: number
  month: number
  congregation_id?: string
  q?: string
  category?: string
  status?: ChecklistStatus
  limit?: number
  offset?: number
}

export interface OccurrenceAction {
  template_id: string
  occurrence_local_date: string
  template_revision: number
}

export interface OccurrenceAccept extends OccurrenceAction {
  local_date_override?: string | null
  local_time_override?: string | null
  title_override?: string | null
  description_override?: string | null
  duration_minutes_override?: number | null
  fold?: 0 | 1 | null
}

export interface OccurrenceResult {
  template_id: string
  occurrence_local_date: string
  status: ChecklistStatus
  planning_slot_id: string | null
}

export interface ResolveRequest extends OccurrenceAction {
  action: 'LINK_EXISTING' | 'MARK_SKIPPED' | 'REOPEN'
  planning_slot_id?: string | null
}

export interface BulkResult extends OccurrenceResult {
  error?: string | null
}

export interface BulkResponse {
  results: Array<Omit<BulkResult, 'status'> & { status: ChecklistStatus | null }>
}

function templatesPath(districtId: string): string {
  return `/api/v1/districts/${encodeURIComponent(districtId)}/recurring-event-templates`
}

function checklistPath(districtId: string): string {
  return `/api/v1/districts/${encodeURIComponent(districtId)}/recurring-event-checklist`
}

function post<T>(url: string, body: unknown): Promise<T> {
  return apiFetch<T>(url, { method: 'POST', body: JSON.stringify(body) })
}

export function listRecurringTemplates(
  districtId: string, limit = 50, offset = 0,
): Promise<RecurringTemplateList> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  return apiFetch<RecurringTemplateList>(`${templatesPath(districtId)}?${params}`)
}

export function createRecurringTemplate(
  districtId: string,
  body: RecurringTemplateInput,
): Promise<RecurringTemplate> {
  return post<RecurringTemplate>(templatesPath(districtId), body)
}

export function updateRecurringTemplate(
  districtId: string,
  templateId: string,
  patch: Partial<RecurringTemplateInput> & { expected_revision: number },
): Promise<RecurringTemplate> {
  return apiFetch<RecurringTemplate>(
    `${templatesPath(districtId)}/${encodeURIComponent(templateId)}`,
    { method: 'PATCH', body: JSON.stringify(patch) },
  )
}

export function listRecurringChecklist(
  districtId: string, filters: ChecklistFilters,
): Promise<ChecklistPage> {
  const params = new URLSearchParams({
    year: String(filters.year),
    month: String(filters.month),
    limit: String(filters.limit ?? 50),
    offset: String(filters.offset ?? 0),
  })
  if (filters.congregation_id) params.set('congregation_id', filters.congregation_id)
  if (filters.q) params.set('q', filters.q)
  if (filters.category) params.set('category', filters.category)
  if (filters.status) params.set('status', filters.status)
  return apiFetch<ChecklistPage>(`${checklistPath(districtId)}?${params}`)
}

export function acceptRecurringOccurrence(
  districtId: string, body: OccurrenceAccept,
): Promise<OccurrenceResult> {
  return post<OccurrenceResult>(`${checklistPath(districtId)}/accept`, body)
}

export function skipRecurringOccurrence(
  districtId: string, body: OccurrenceAction,
): Promise<OccurrenceResult> {
  return post<OccurrenceResult>(`${checklistPath(districtId)}/skip`, body)
}

export function reopenRecurringOccurrence(
  districtId: string, body: OccurrenceAction,
): Promise<OccurrenceResult> {
  return post<OccurrenceResult>(`${checklistPath(districtId)}/reopen`, body)
}

export function resolveRecurringOccurrence(
  districtId: string, body: ResolveRequest,
): Promise<OccurrenceResult> {
  return post<OccurrenceResult>(`${checklistPath(districtId)}/resolve`, body)
}

export function bulkAcceptRecurringOccurrences(
  districtId: string, items: OccurrenceAccept[],
): Promise<BulkResponse> {
  return post<BulkResponse>(`${checklistPath(districtId)}/bulk-accept`, { items })
}
