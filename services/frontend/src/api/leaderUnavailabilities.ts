import { apiFetch } from './client'

export type UnavailabilityReason = 'URLAUB' | 'SPERRZEIT' | 'FORTBILDUNG' | 'SONSTIGES'

export const UNAVAILABILITY_REASONS: { value: UnavailabilityReason; label: string }[] = [
  { value: 'URLAUB', label: 'Urlaub' },
  { value: 'SPERRZEIT', label: 'Sperrzeit' },
  { value: 'FORTBILDUNG', label: 'Fortbildung' },
  { value: 'SONSTIGES', label: 'Sonstiges' },
]

export function unavailabilityReasonLabel(reason: UnavailabilityReason): string {
  return UNAVAILABILITY_REASONS.find((r) => r.value === reason)?.label ?? reason
}

export function formatUnavailabilityPeriod(item: LeaderUnavailabilityResponse): string {
  const start = new Date(item.start_at)
  const end = new Date(item.end_at)
  const locale = 'de-DE'
  return start.toDateString() === end.toDateString()
    ? start.toLocaleDateString(locale)
    : `${start.toLocaleDateString(locale)} – ${end.toLocaleDateString(locale)}`
}

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

export function listUnavailabilities(
  districtId: string,
  leaderId?: string,
): Promise<LeaderUnavailabilityResponse[]> {
  const query = leaderId ? `?leader_id=${encodeURIComponent(leaderId)}` : ''
  return apiFetch<LeaderUnavailabilityResponse[]>(
    `/api/v1/districts/${districtId}/leader-unavailabilities${query}`,
  )
}

export function createUnavailability(
  districtId: string,
  body: LeaderUnavailabilityCreate,
): Promise<LeaderUnavailabilityResponse> {
  return apiFetch<LeaderUnavailabilityResponse>(
    `/api/v1/districts/${districtId}/leader-unavailabilities`,
    {
      method: 'POST',
      body: JSON.stringify(body),
    },
  )
}

export function deleteUnavailability(districtId: string, unavailabilityId: string): Promise<void> {
  return apiFetch<void>(
    `/api/v1/districts/${districtId}/leader-unavailabilities/${unavailabilityId}`,
    {
      method: 'DELETE',
    },
  )
}
