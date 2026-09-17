import { apiFetch } from './client'

export type UnavailabilityReason = 'URLAUB' | 'SPERRZEIT' | 'FORTBILDUNG' | 'SONSTIGES'

export interface LeaderUnavailabilityResponse {
  id: string
  leader_id: string
  start_at: string
  end_at: string
  reason: UnavailabilityReason
  note: string | null
  created_at: string
  updated_at: string
}

export interface LeaderUnavailabilityCreate {
  leader_id: string
  start_at: string
  end_at: string
  reason: UnavailabilityReason
  note?: string | null
}

const basePath = (districtId: string) =>
  `/api/v1/districts/${districtId}/leader-unavailabilities`

export function listLeaderUnavailabilities(
  districtId: string,
  leaderId?: string,
): Promise<LeaderUnavailabilityResponse[]> {
  const query = leaderId ? `?leader_id=${encodeURIComponent(leaderId)}` : ''
  return apiFetch<LeaderUnavailabilityResponse[]>(`${basePath(districtId)}${query}`)
}

export function createLeaderUnavailability(
  districtId: string,
  body: LeaderUnavailabilityCreate,
): Promise<LeaderUnavailabilityResponse> {
  return apiFetch<LeaderUnavailabilityResponse>(basePath(districtId), {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function deleteLeaderUnavailability(
  districtId: string,
  unavailabilityId: string,
): Promise<void> {
  return apiFetch<void>(`${basePath(districtId)}/${unavailabilityId}`, {
    method: 'DELETE',
  })
}
