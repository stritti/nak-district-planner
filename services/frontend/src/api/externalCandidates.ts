import { apiFetch } from './client'

export type CandidateStatus = 'PENDING' | 'ACCEPTED' | 'DISMISSED'

export interface ExternalEventCandidate {
  id: string
  district_id: string
  calendar_integration_id: string
  external_event_id: string
  source: string
  congregation_id: string | null
  title: string
  category: string | null
  start_at: string
  end_at: string
  event_date: string
  event_time: string
  description: string | null
  status: CandidateStatus
  matched_slot_id: string | null
  created_at: string
  updated_at: string
  reviewed_at: string | null
  reviewed_by: string | null
}

export function listExternalCandidates(
  districtId: string,
  status: CandidateStatus = 'PENDING',
): Promise<ExternalEventCandidate[]> {
  const params = new URLSearchParams({ district_id: districtId, status })
  return apiFetch(`/api/v1/external-candidates?${params}`)
}

export function acceptExternalCandidate(
  candidateId: string,
  matchedSlotId?: string,
): Promise<ExternalEventCandidate> {
  return apiFetch(`/api/v1/external-candidates/${candidateId}/accept`, {
    method: 'POST',
    body: JSON.stringify({ matched_slot_id: matchedSlotId ?? null }),
  })
}

export function dismissExternalCandidate(candidateId: string): Promise<ExternalEventCandidate> {
  return apiFetch(`/api/v1/external-candidates/${candidateId}/dismiss`, {
    method: 'POST',
  })
}
