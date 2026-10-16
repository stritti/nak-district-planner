// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { apiFetch } from './client'

export interface ServiceAssignmentResponse {
  id: string
  event_id: string
  leader_id: string | null
  leader_name: string | null
  status: 'OPEN' | 'ASSIGNED' | 'CONFIRMED'
  created_at: string
  updated_at: string
}

export interface AssignmentOptions {
  leaderId?: string | null
  leaderName?: string | null
  confirmWarnings?: boolean
}

export type AssignmentStatus = 'OPEN' | 'ASSIGNED' | 'CONFIRMED'

/** Saved assignment plus the event revision valid after the write. */
export interface AssignmentWriteResult extends ServiceAssignmentResponse {
  event_revision: string
}

const MISSING_REVISION = 'Versionsinformation fehlt. Bitte neu laden.'

/**
 * Dialog writers share the event's strong revision with inline cells (428 without, 412 if
 * stale), so a dialog save can never silently overwrite an inline change.
 */
export function createAssignment(
  eventId: string,
  options: AssignmentOptions,
  revision: string,
  assignmentStatus: AssignmentStatus = 'ASSIGNED',
): Promise<AssignmentWriteResult> {
  if (!revision) return Promise.reject(new Error(MISSING_REVISION))
  return apiFetch<AssignmentWriteResult>(`/api/v1/events/${eventId}/assignments`, {
    method: 'POST',
    headers: { 'If-Match': revision },
    body: JSON.stringify({
      leader_id: options.leaderId ?? null,
      leader_name: options.leaderName ?? null,
      status: assignmentStatus,
      ...(options.confirmWarnings !== undefined ? { confirm_warnings: options.confirmWarnings } : {}),
    }),
  })
}

export function updateAssignment(
  eventId: string,
  assignmentId: string,
  options: AssignmentOptions,
  revision: string,
  assignmentStatus?: AssignmentStatus,
): Promise<AssignmentWriteResult> {
  if (!revision) return Promise.reject(new Error(MISSING_REVISION))
  return apiFetch<AssignmentWriteResult>(
    `/api/v1/events/${eventId}/assignments/${assignmentId}`,
    {
      method: 'PUT',
      headers: { 'If-Match': revision },
      body: JSON.stringify({
        leader_id: options.leaderId ?? null,
        leader_name: options.leaderName ?? null,
        ...(assignmentStatus ? { status: assignmentStatus } : {}),
        ...(options.confirmWarnings !== undefined ? { confirm_warnings: options.confirmWarnings } : {}),
      }),
    },
  )
}

export function deleteAssignment(
  eventId: string,
  assignmentId: string,
  revision: string,
): Promise<void> {
  if (!revision) return Promise.reject(new Error(MISSING_REVISION))
  return apiFetch<void>(`/api/v1/events/${eventId}/assignments/${assignmentId}`, {
    method: 'DELETE',
    headers: { 'If-Match': revision },
  })
}

/** Optimistic, non-destructive minister assignment for inline UI adapters. */
export type InlineAssignmentResult = AssignmentWriteResult

export function changeAssignmentInline(
  eventId: string,
  leaderId: string,
  revision: string,
  confirmWarnings = false,
): Promise<InlineAssignmentResult> {
  if (!revision) return Promise.reject(new Error(MISSING_REVISION))
  if (!leaderId) return Promise.reject(new Error('Zum Zuweisen ist eine Person erforderlich.'))
  return apiFetch<InlineAssignmentResult>(`/api/v1/events/${eventId}/assignments/inline`, {
    method: 'PUT',
    headers: { 'If-Match': revision },
    body: JSON.stringify({ leader_id: leaderId, confirm_warnings: confirmWarnings }),
  })
}
