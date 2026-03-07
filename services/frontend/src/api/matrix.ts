import { apiFetch } from './client'

export interface MatrixCell {
  event_id: string | null
  event_title: string | null
  category: string | null
  is_gap: boolean
  assignment_id: string | null
  assignment_status: 'OPEN' | 'ASSIGNED' | 'CONFIRMED' | null
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
}

export function fetchMatrix(
  districtId: string,
  fromDt: string,
  toDt: string,
): Promise<MatrixResponse> {
  const params = new URLSearchParams({ from_dt: fromDt, to_dt: toDt })
  return apiFetch<MatrixResponse>(`/api/v1/districts/${districtId}/matrix?${params}`)
}
