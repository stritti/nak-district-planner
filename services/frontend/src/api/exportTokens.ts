import { apiFetch } from './client'

export type TokenType = 'PUBLIC' | 'INTERNAL'

export interface ExportTokenResponse {
  id: string
  token: string
  label: string
  token_type: TokenType
  district_id: string
  congregation_id: string | null
  leader_id: string | null
  created_at: string
}

export interface ExportTokenCreate {
  label: string
  token_type: TokenType
  district_id: string
  congregation_id?: string | null
  leader_id?: string | null
}

export function listExportTokens(district_id?: string): Promise<ExportTokenResponse[]> {
  const params = district_id ? `?district_id=${district_id}` : ''
  return apiFetch(`/api/v1/export-tokens${params}`)
}

export function createExportToken(data: ExportTokenCreate): Promise<ExportTokenResponse> {
  return apiFetch('/api/v1/export-tokens', { method: 'POST', body: JSON.stringify(data) })
}

export function deleteExportToken(id: string): Promise<void> {
  return apiFetch(`/api/v1/export-tokens/${id}`, { method: 'DELETE' })
}
