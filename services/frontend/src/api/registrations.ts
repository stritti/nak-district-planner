import { apiFetch } from './client'
import type { LeaderRank, SpecialRole } from './leaders'

export type RegistrationStatus = 'PENDING' | 'APPROVED' | 'REJECTED'

export interface RegistrationResponse {
  id: string
  district_id: string
  name: string
  email: string
  rank: LeaderRank | null
  congregation_id: string | null
  special_role: SpecialRole | null
  phone: string | null
  notes: string | null
  status: RegistrationStatus
  rejection_reason: string | null
  user_sub: string | null
  created_at: string
  updated_at: string
}

export interface RegistrationCreate {
  name: string
  email: string
  rank?: LeaderRank | null
  congregation_id?: string | null
  special_role?: SpecialRole | null
  phone?: string | null
  notes?: string | null
}

export interface RegistrationApprove {
  congregation_id?: string | null
  rank?: LeaderRank | null
  special_role?: SpecialRole | null
}

export interface RegistrationReject {
  reason?: string | null
}

/** Submit a self-registration (public — no auth required). */
export function submitRegistration(
  districtId: string,
  body: RegistrationCreate,
): Promise<RegistrationResponse> {
  return apiFetch<RegistrationResponse>(
    `/api/v1/districts/${districtId}/registrations`,
    {
      method: 'POST',
      body: JSON.stringify(body),
    },
  )
}

/** List registrations for a district (DISTRICT_ADMIN only). */
export function listRegistrations(
  districtId: string,
  status?: RegistrationStatus,
): Promise<RegistrationResponse[]> {
  const qs = status ? `?status=${status}` : ''
  return apiFetch<RegistrationResponse[]>(
    `/api/v1/districts/${districtId}/registrations${qs}`,
  )
}

/** Approve a registration (DISTRICT_ADMIN only). */
export function approveRegistration(
  districtId: string,
  registrationId: string,
  body: RegistrationApprove = {},
): Promise<RegistrationResponse> {
  return apiFetch<RegistrationResponse>(
    `/api/v1/districts/${districtId}/registrations/${registrationId}/approve`,
    {
      method: 'POST',
      body: JSON.stringify(body),
    },
  )
}

/** Reject a registration (DISTRICT_ADMIN only). */
export function rejectRegistration(
  districtId: string,
  registrationId: string,
  body: RegistrationReject = {},
): Promise<RegistrationResponse> {
  return apiFetch<RegistrationResponse>(
    `/api/v1/districts/${districtId}/registrations/${registrationId}/reject`,
    {
      method: 'POST',
      body: JSON.stringify(body),
    },
  )
}

/** Delete a registration (DISTRICT_ADMIN only). */
export function deleteRegistration(districtId: string, registrationId: string): Promise<void> {
  return apiFetch<void>(
    `/api/v1/districts/${districtId}/registrations/${registrationId}`,
    { method: 'DELETE' },
  )
}
