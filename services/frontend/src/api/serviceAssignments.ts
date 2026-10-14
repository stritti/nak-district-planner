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

export function createAssignment(
  eventId: string,
  options: AssignmentOptions,
  assignmentStatus: AssignmentStatus = 'ASSIGNED',
): Promise<ServiceAssignmentResponse> {
  return apiFetch<ServiceAssignmentResponse>(`/api/v1/events/${eventId}/assignments`, {
    method: 'POST',
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
  assignmentStatus?: AssignmentStatus,
): Promise<ServiceAssignmentResponse> {
  return apiFetch<ServiceAssignmentResponse>(
    `/api/v1/events/${eventId}/assignments/${assignmentId}`,
    {
      method: 'PUT',
      body: JSON.stringify({
        leader_id: options.leaderId ?? null,
        leader_name: options.leaderName ?? null,
        ...(assignmentStatus ? { status: assignmentStatus } : {}),
        ...(options.confirmWarnings !== undefined ? { confirm_warnings: options.confirmWarnings } : {}),
      }),
    },
  )
}

export function deleteAssignment(eventId: string, assignmentId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/events/${eventId}/assignments/${assignmentId}`, {
    method: 'DELETE',
  })
}

/** Optimistic, non-destructive minister assignment for inline UI adapters. */
export interface InlineAssignmentResult extends ServiceAssignmentResponse {
  event_revision: string
}

export function changeAssignmentInline(
  eventId: string,
  leaderId: string,
  revision: string,
  confirmWarnings = false,
): Promise<InlineAssignmentResult> {
  if (!revision) return Promise.reject(new Error('Versionsinformation fehlt. Bitte neu laden.'))
  if (!leaderId) return Promise.reject(new Error('Zum Zuweisen ist eine Person erforderlich.'))
  return apiFetch<InlineAssignmentResult>(`/api/v1/events/${eventId}/assignments/inline`, {
    method: 'PUT',
    headers: { 'If-Match': revision },
    body: JSON.stringify({ leader_id: leaderId, confirm_warnings: confirmWarnings }),
  })
}
