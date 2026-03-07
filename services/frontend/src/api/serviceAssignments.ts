import { apiFetch } from './client'

export interface ServiceAssignmentResponse {
  id: string
  event_id: string
  leader_name: string
  status: 'OPEN' | 'ASSIGNED' | 'CONFIRMED'
  created_at: string
  updated_at: string
}

export function createAssignment(
  eventId: string,
  leaderName: string,
  assignmentStatus: 'OPEN' | 'ASSIGNED' | 'CONFIRMED' = 'ASSIGNED',
): Promise<ServiceAssignmentResponse> {
  return apiFetch<ServiceAssignmentResponse>(`/api/v1/events/${eventId}/assignments`, {
    method: 'POST',
    body: JSON.stringify({ leader_name: leaderName, status: assignmentStatus }),
  })
}
