import { apiFetch } from './client'

export interface CurrentUserResponse {
  sub: string
  email: string
  username: string
  name: string | null
  given_name: string | null
  family_name: string | null
  is_superadmin: boolean
}

export interface MembershipAccess {
  role: string
  scope_type: 'DISTRICT' | 'CONGREGATION'
  scope_id: string
}

export interface AccessContextResponse {
  status: 'ACTIVE' | 'PENDING_APPROVAL'
  memberships: MembershipAccess[]
}

export function getCurrentUser(): Promise<CurrentUserResponse> {
  return apiFetch<CurrentUserResponse>('/api/v1/auth/me')
}

export function getAccessContext(): Promise<AccessContextResponse> {
  return apiFetch<AccessContextResponse>('/api/v1/auth/access')
}
