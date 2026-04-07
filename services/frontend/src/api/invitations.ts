import { apiFetch } from './client'

export type InvitationTargetType = 'DISTRICT_CONGREGATION' | 'EXTERNAL_NOTE'
export type OverwriteDecisionStatus = 'PENDING_OVERWRITE' | 'ACCEPTED' | 'REJECTED'

export interface InvitationTargetCreate {
  target_type: InvitationTargetType
  target_congregation_id?: string | null
  external_target_note?: string | null
}

export interface InvitationResponse {
  id: string
  source_event_id: string
  source_congregation_id: string
  target_type: InvitationTargetType
  target_congregation_id: string | null
  external_target_note: string | null
  linked_event_id: string | null
  created_at: string
  updated_at: string
}

export interface OverwriteRequestResponse {
  id: string
  invitation_id: string
  source_event_id: string
  source_event_title: string | null
  target_event_id: string
  target_event_title: string | null
  target_congregation_id: string | null
  current_title: string | null
  current_start_at: string | null
  current_end_at: string | null
  current_description: string | null
  current_category: string | null
  proposed_title: string
  proposed_start_at: string
  proposed_end_at: string
  proposed_description: string | null
  proposed_category: string | null
  status: OverwriteDecisionStatus
  decided_at: string | null
  created_at: string
  updated_at: string
}

export function createInvitations(
  eventId: string,
  targets: InvitationTargetCreate[],
): Promise<InvitationResponse[]> {
  return apiFetch(`/api/v1/events/${eventId}/invitations`, {
    method: 'POST',
    body: JSON.stringify({ targets }),
  })
}

export function listEventInvitations(eventId: string): Promise<InvitationResponse[]> {
  return apiFetch(`/api/v1/events/${eventId}/invitations`)
}

export function deleteInvitation(invitationId: string): Promise<void> {
  return apiFetch(`/api/v1/invitations/${invitationId}`, {
    method: 'DELETE',
  })
}

export function listOverwriteRequests(districtId: string): Promise<OverwriteRequestResponse[]> {
  const params = new URLSearchParams({ district_id: districtId })
  return apiFetch(`/api/v1/invitations/overwrite-requests?${params.toString()}`)
}

export function decideOverwriteRequest(
  requestId: string,
  decision: 'ACCEPTED' | 'REJECTED',
): Promise<OverwriteRequestResponse> {
  return apiFetch(`/api/v1/invitations/overwrite-requests/${requestId}/decision`, {
    method: 'POST',
    body: JSON.stringify({ decision }),
  })
}
