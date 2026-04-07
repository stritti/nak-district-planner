import { apiFetch } from './client'

export interface ServiceTime {
  weekday: number  // 0=Mo … 6=So
  time: string     // "HH:MM"
}

export interface DistrictResponse {
  id: string
  name: string
  state_code: string | null
  created_at: string
  updated_at: string
}

export interface CongregationResponse {
  id: string
  name: string
  district_id: string
  group_id: string | null
  service_times: ServiceTime[]
  created_at: string
  updated_at: string
}

export interface CongregationGroupResponse {
  id: string
  name: string
  district_id: string
  created_at: string
  updated_at: string
}

export function listDistricts(): Promise<DistrictResponse[]> {
  return apiFetch('/api/v1/districts')
}

export function createDistrict(name: string, stateCode?: string | null): Promise<DistrictResponse> {
  return apiFetch('/api/v1/districts', {
    method: 'POST',
    body: JSON.stringify({ name, state_code: stateCode ?? null }),
  })
}

export function updateDistrict(
  id: string,
  payload: { name?: string; state_code?: string | null },
): Promise<DistrictResponse> {
  return apiFetch(`/api/v1/districts/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function listCongregations(
  districtId: string,
  groupId?: string,
): Promise<CongregationResponse[]> {
  const url = groupId
    ? `/api/v1/districts/${districtId}/congregations?group_id=${groupId}`
    : `/api/v1/districts/${districtId}/congregations`
  return apiFetch(url)
}

export function createCongregation(
  districtId: string,
  name: string,
  serviceTimes?: ServiceTime[],
  groupId?: string | null,
): Promise<CongregationResponse> {
  return apiFetch(`/api/v1/districts/${districtId}/congregations`, {
    method: 'POST',
    body: JSON.stringify({
      name,
      service_times: serviceTimes ?? null,
      group_id: groupId ?? null,
    }),
  })
}

export function updateCongregation(
  districtId: string,
  congregationId: string,
  payload: { name?: string; service_times?: ServiceTime[]; group_id?: string | null },
): Promise<CongregationResponse> {
  return apiFetch(`/api/v1/districts/${districtId}/congregations/${congregationId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

// --- Congregation Groups ---

export function listGroups(districtId: string): Promise<CongregationGroupResponse[]> {
  return apiFetch(`/api/v1/districts/${districtId}/groups`)
}

export function createGroup(districtId: string, name: string): Promise<CongregationGroupResponse> {
  return apiFetch(`/api/v1/districts/${districtId}/groups`, {
    method: 'POST',
    body: JSON.stringify({ name }),
  })
}

export function updateGroup(
  districtId: string,
  groupId: string,
  name: string,
): Promise<CongregationGroupResponse> {
  return apiFetch(`/api/v1/districts/${districtId}/groups/${groupId}`, {
    method: 'PATCH',
    body: JSON.stringify({ name }),
  })
}

export function deleteGroup(districtId: string, groupId: string): Promise<void> {
  return apiFetch(`/api/v1/districts/${districtId}/groups/${groupId}`, {
    method: 'DELETE',
  })
}

export interface FeiertageImportResult {
  created: number
  updated: number
  skipped: number
}

export interface MatrixDraftGenerationResult {
  districts: number
  congregations: number
  created: number
  skipped_existing: number
  adopted_existing: number
  invalid_configurations: number
  generated_in_requested_range: number
}

export function listDeStates(districtId: string): Promise<Record<string, string>> {
  return apiFetch(`/api/v1/districts/${districtId}/feiertage/states`)
}

export function importFeiertage(
  districtId: string,
  year: number,
  stateCode: string | null,
): Promise<FeiertageImportResult> {
  return apiFetch(`/api/v1/districts/${districtId}/feiertage`, {
    method: 'POST',
    body: JSON.stringify({ year, state_code: stateCode }),
  })
}

export function generateMatrixDraftServices(
  districtId: string,
  fromDt: string,
  toDt: string,
): Promise<MatrixDraftGenerationResult> {
  const params = new URLSearchParams({ from_dt: fromDt, to_dt: toDt })
  return apiFetch(`/api/v1/districts/${districtId}/matrix/generate-drafts?${params}`, {
    method: 'POST',
  })
}
