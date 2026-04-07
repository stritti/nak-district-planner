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

export function getCurrentUser(): Promise<CurrentUserResponse> {
  return apiFetch<CurrentUserResponse>('/api/v1/auth/me')
}
