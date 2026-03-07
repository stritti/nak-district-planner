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
  service_times: ServiceTime[]
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

export function listCongregations(districtId: string): Promise<CongregationResponse[]> {
  return apiFetch(`/api/v1/districts/${districtId}/congregations`)
}

export function createCongregation(
  districtId: string,
  name: string,
  serviceTimes?: ServiceTime[],
): Promise<CongregationResponse> {
  return apiFetch(`/api/v1/districts/${districtId}/congregations`, {
    method: 'POST',
    body: JSON.stringify({ name, service_times: serviceTimes ?? null }),
  })
}

export function updateCongregation(
  districtId: string,
  congregationId: string,
  payload: { name?: string; service_times?: ServiceTime[] },
): Promise<CongregationResponse> {
  return apiFetch(`/api/v1/districts/${districtId}/congregations/${congregationId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export interface FeiertageImportResult {
  created: number
  updated: number
  skipped: number
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
