import { apiFetch } from './client'

export const LEADER_RANKS = [
  { value: 'Di.',    label: 'Di. – Diakon' },
  { value: 'Pr.',    label: 'Pr. – Priester' },
  { value: 'Ev.',    label: 'Ev. – Evangelist' },
  { value: 'Hi.',    label: 'Hi. – Hirte' },
  { value: 'BE',     label: 'BE – Bezirksevangelist' },
  { value: 'BÄ',     label: 'BÄ – Bezirksältester' },
  { value: 'Bi.',    label: 'Bi. – Bischof' },
  { value: 'Ap.',    label: 'Ap. – Apostel' },
  { value: 'BezAp.', label: 'BezAp. – Bezirksapostel' },
  { value: 'StAp.',  label: 'StAp. – Stammapostel' },
] as const

export type LeaderRank = (typeof LEADER_RANKS)[number]['value']

export const SPECIAL_ROLES = [
  { value: 'Gemeindevorsteher', label: 'Gemeindevorsteher' },
  { value: 'Bezirksvorsteher',  label: 'Bezirksvorsteher' },
] as const

export type SpecialRole = (typeof SPECIAL_ROLES)[number]['value']

export interface LeaderResponse {
  id: string
  name: string
  district_id: string
  rank: LeaderRank | null
  congregation_id: string | null
  special_role: SpecialRole | null
  user_sub: string | null
  email: string | null
  phone: string | null
  notes: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface LeaderSelfLinkResponse {
  linked: boolean
  leader: LeaderResponse | null
}

export interface LeaderCreate {
  name: string
  rank: LeaderRank
  congregation_id?: string | null
  special_role?: SpecialRole | null
  email?: string | null
  phone?: string | null
  notes?: string | null
  is_active?: boolean
}

export interface LeaderUpdate {
  name?: string
  rank?: LeaderRank | null
  congregation_id?: string | null
  special_role?: SpecialRole | null
  email?: string | null
  phone?: string | null
  notes?: string | null
  is_active?: boolean
}

export function listLeaders(districtId: string): Promise<LeaderResponse[]> {
  return apiFetch<LeaderResponse[]>(`/api/v1/districts/${districtId}/leaders`)
}

export function createLeader(districtId: string, body: LeaderCreate): Promise<LeaderResponse> {
  return apiFetch<LeaderResponse>(`/api/v1/districts/${districtId}/leaders`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function updateLeader(
  districtId: string,
  leaderId: string,
  body: LeaderUpdate,
): Promise<LeaderResponse> {
  return apiFetch<LeaderResponse>(`/api/v1/districts/${districtId}/leaders/${leaderId}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export function deleteLeader(districtId: string, leaderId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/districts/${districtId}/leaders/${leaderId}`, {
    method: 'DELETE',
  })
}

export function getSelfLeaderLink(districtId: string): Promise<LeaderSelfLinkResponse> {
  return apiFetch<LeaderSelfLinkResponse>(`/api/v1/districts/${districtId}/leaders/link-self`)
}

export function linkSelfToLeader(districtId: string, leaderId: string): Promise<LeaderSelfLinkResponse> {
  return apiFetch<LeaderSelfLinkResponse>(`/api/v1/districts/${districtId}/leaders/link-self`, {
    method: 'POST',
    body: JSON.stringify({ leader_id: leaderId }),
  })
}

export function unlinkSelfFromLeader(districtId: string): Promise<LeaderSelfLinkResponse> {
  return apiFetch<LeaderSelfLinkResponse>(`/api/v1/districts/${districtId}/leaders/link-self`, {
    method: 'DELETE',
  })
}
