import { apiFetch } from './client'

export interface ServiceTime {
  weekday: number  // 0=Mo … 6=So
  time: string     // "HH:MM"
}

export interface DistrictResponse {
  id: string
  name: string
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

export function createDistrict(name: string): Promise<DistrictResponse> {
  return apiFetch('/api/v1/districts', {
    method: 'POST',
    body: JSON.stringify({ name }),
  })
}

export function updateDistrict(id: string, name: string): Promise<DistrictResponse> {
  return apiFetch(`/api/v1/districts/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ name }),
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
