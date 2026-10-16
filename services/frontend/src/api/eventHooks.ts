// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { apiFetch } from './client'
import type { RecipientRole } from './reminderConfigs'

export type EventType =
  | 'SLOT_UNASSIGNED'
  | 'EXTERNAL_EVENT_DETECTED'
  | 'SYNC_ERROR'
  | 'REGISTRATION_RECEIVED'
  | 'ASSIGNMENT_CONFIRMED'
  | 'PLAN_FINALIZED'

export interface EventHookInput {
  recipient_role: RecipientRole
  subject_template: string
  body_template: string
  is_active: boolean
}

export interface EventHookCreateInput extends EventHookInput {
  event_type: EventType
}

export interface EventHook extends EventHookCreateInput {
  id: string
  district_id: string
  created_at: string
  updated_at: string
  revision: string
}

export interface EventTypeInfo {
  event_type: EventType
  placeholders: string[]
}

const baseUrl = (districtId: string) =>
  `/api/v1/districts/${encodeURIComponent(districtId)}/event-hooks`

export function listEventHooks(districtId: string): Promise<EventHook[]> {
  return apiFetch(baseUrl(districtId))
}

export function listEventTypes(districtId: string): Promise<EventTypeInfo[]> {
  return apiFetch(`${baseUrl(districtId)}/event-types`)
}

export function createEventHook(districtId: string, input: EventHookCreateInput): Promise<EventHook> {
  return apiFetch(baseUrl(districtId), { method: 'POST', body: JSON.stringify(input) })
}

/** PUT replaces all mutable fields; the event type of a hook cannot change. */
export function updateEventHook(
  districtId: string,
  hookId: string,
  input: EventHookInput,
  revision: string,
): Promise<EventHook> {
  if (!revision) return Promise.reject(new Error('Versionsinformation fehlt. Bitte neu laden.'))
  return apiFetch(`${baseUrl(districtId)}/${encodeURIComponent(hookId)}`, {
    method: 'PUT',
    headers: { 'If-Match': revision },
    body: JSON.stringify(input),
  })
}

/** Soft-deactivates; the response is the updated hook with its new revision. */
export function deactivateEventHook(
  districtId: string,
  hookId: string,
  revision: string,
): Promise<EventHook> {
  if (!revision) return Promise.reject(new Error('Versionsinformation fehlt. Bitte neu laden.'))
  return apiFetch(`${baseUrl(districtId)}/${encodeURIComponent(hookId)}`, {
    method: 'DELETE',
    headers: { 'If-Match': revision },
  })
}
