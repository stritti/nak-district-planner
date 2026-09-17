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

export interface ConflictItem {
  rule_id: string
  severity: 'PASS' | 'WARN' | 'BLOCK'
  message: string
  details: Record<string, unknown>
}

export interface ConflictResponse {
  conflicts: ConflictItem[]
}

export function createAssignment(
  eventId: string,
  options: { leaderId?: string | null; leaderName?: string | null },
  assignmentStatus: 'OPEN' | 'ASSIGNED' | 'CONFIRMED' = 'ASSIGNED',
  confirmWarnings = false,
): Promise<ServiceAssignmentResponse> {
  return apiFetch<ServiceAssignmentResponse>(`/api/v1/events/${eventId}/assignments`, {
    method: 'POST',
    body: JSON.stringify({
      leader_id: options.leaderId ?? null,
      leader_name: options.leaderName ?? null,
      status: assignmentStatus,
      confirm_warnings: confirmWarnings,
    }),
  })
}

export function updateAssignment(
  eventId: string,
  assignmentId: string,
  options: { leaderId?: string | null; leaderName?: string | null },
  assignmentStatus?: 'OPEN' | 'ASSIGNED' | 'CONFIRMED',
  confirmWarnings = false,
): Promise<ServiceAssignmentResponse> {
  return apiFetch<ServiceAssignmentResponse>(
    `/api/v1/events/${eventId}/assignments/${assignmentId}`,
    {
      method: 'PUT',
      body: JSON.stringify({
        leader_id: options.leaderId ?? null,
        leader_name: options.leaderName ?? null,
        ...(assignmentStatus ? { status: assignmentStatus } : {}),
        confirm_warnings: confirmWarnings,
      }),
    },
  )
}

export function deleteAssignment(eventId: string, assignmentId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/events/${eventId}/assignments/${assignmentId}`, {
    method: 'DELETE',
  })
}
