import { apiFetch } from './client'

export interface MatrixCell {
  event_id: string | null
  assignment_event_id?: string | null
  invitation_source_congregation_name?: string | null
  invitation_count?: number
  event_title: string | null
  category: string | null
  is_gap: boolean
  is_assignment_editable?: boolean
  assignment_id: string | null
  assignment_status: 'OPEN' | 'ASSIGNED' | 'CONFIRMED' | null
  leader_id: string | null
  leader_name: string | null
}

export interface MatrixRow {
  congregation_id: string
  congregation_name: string
  cells: Record<string, MatrixCell>
}

export interface MatrixResponse {
  dates: string[]
  rows: MatrixRow[]
  holidays: Record<string, string[]>
}

export function fetchMatrix(
  districtId: string,
  fromDt: string,
  toDt: string,
  groupId?: string,
): Promise<MatrixResponse> {
  const params = new URLSearchParams({ from_dt: fromDt, to_dt: toDt })
  if (groupId) params.append('group_id', groupId)
  return apiFetch<MatrixResponse>(`/api/v1/districts/${districtId}/matrix?${params}`)
}
