import { apiFetch } from './client'
import type { LeaderRank, SpecialRole } from './leaders'

type ScopeType = 'DISTRICT' | 'CONGREGATION'

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
  assigned_role: 'DISTRICT_ADMIN' | 'CONGREGATION_ADMIN' | 'PLANNER' | 'VIEWER' | null
  assigned_scope_type: ScopeType | null
  assigned_scope_id: string | null
  approved_by_sub: string | null
  approved_at: string | null
  idp_provision_status: string | null
  idp_provision_error: string | null
  idp_provisioned_at: string | null
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
  role: 'DISTRICT_ADMIN' | 'CONGREGATION_ADMIN' | 'PLANNER' | 'VIEWER'
  scope_type: ScopeType
  scope_id: string
  congregation_id?: string | null
  rank?: LeaderRank | null
  special_role?: SpecialRole | null
}

export interface RegistrationReject {
  reason?: string | null
}

export interface RegistrationPendingCount {
  district_id: string
  pending: number
}

export interface RegistrationPendingOverview {
  total_pending: number
  by_district: RegistrationPendingCount[]
}

/** Minimal district info from the public endpoint. */
export interface PublicDistrictInfo {
  id: string
  name: string
}

/** Minimal congregation info from the public endpoint. */
export interface PublicCongregationInfo {
  id: string
  name: string
}

/**
 * Unauthenticated fetch helper for public endpoints.
 * Avoids the auth-aware `apiFetch` wrapper, which would attempt token refresh
 * and potentially redirect unauthenticated users to login.
 */
async function publicFetch<T>(url: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers as Record<string, string>) },
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`${res.status} ${res.statusText}${text ? ': ' + text : ''}`)
  }
  if (res.status === 204 || res.headers.get('content-length') === '0') {
    return undefined as T
  }
  return res.json() as Promise<T>
}

/** List all districts — public, no auth required. */
export function listDistrictsPublic(): Promise<PublicDistrictInfo[]> {
  return publicFetch<PublicDistrictInfo[]>('/api/v1/public/districts')
}

/** List congregations for a district — public, no auth required. */
export function listCongregationsPublic(districtId: string): Promise<PublicCongregationInfo[]> {
  return publicFetch<PublicCongregationInfo[]>(
    `/api/v1/public/districts/${districtId}/congregations`,
  )
}

/** Submit a self-registration (public — no auth required). */
export function submitRegistration(
  districtId: string,
  body: RegistrationCreate,
): Promise<RegistrationResponse> {
  return publicFetch<RegistrationResponse>(
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
  body: RegistrationApprove,
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

export function getPendingRegistrationsOverview(): Promise<RegistrationPendingOverview> {
  return apiFetch<RegistrationPendingOverview>('/api/v1/registrations/pending-overview')
}
