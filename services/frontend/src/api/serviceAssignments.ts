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

export function createAssignment(
  eventId: string,
  options: { leaderId?: string | null; leaderName?: string | null },
  assignmentStatus: 'OPEN' | 'ASSIGNED' | 'CONFIRMED' = 'ASSIGNED',
): Promise<ServiceAssignmentResponse> {
  return apiFetch<ServiceAssignmentResponse>(`/api/v1/events/${eventId}/assignments`, {
    method: 'POST',
    body: JSON.stringify({
      leader_id: options.leaderId ?? null,
      leader_name: options.leaderName ?? null,
      status: assignmentStatus,
    }),
  })
}

export function updateAssignment(
  eventId: string,
  assignmentId: string,
  options: { leaderId?: string | null; leaderName?: string | null },
  assignmentStatus?: 'OPEN' | 'ASSIGNED' | 'CONFIRMED',
): Promise<ServiceAssignmentResponse> {
  return apiFetch<ServiceAssignmentResponse>(
    `/api/v1/events/${eventId}/assignments/${assignmentId}`,
    {
      method: 'PUT',
      body: JSON.stringify({
        leader_id: options.leaderId ?? null,
        leader_name: options.leaderName ?? null,
        ...(assignmentStatus ? { status: assignmentStatus } : {}),
      }),
    },
  )
}

export function deleteAssignment(eventId: string, assignmentId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/events/${eventId}/assignments/${assignmentId}`, {
    method: 'DELETE',
  })
}
