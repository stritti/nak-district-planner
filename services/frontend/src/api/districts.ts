import { apiFetch } from './client'

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

export function createCongregation(districtId: string, name: string): Promise<CongregationResponse> {
  return apiFetch(`/api/v1/districts/${districtId}/congregations`, {
    method: 'POST',
    body: JSON.stringify({ name }),
  })
}

export function updateCongregation(
  districtId: string,
  congregationId: string,
  name: string,
): Promise<CongregationResponse> {
  return apiFetch(`/api/v1/districts/${districtId}/congregations/${congregationId}`, {
    method: 'PATCH',
    body: JSON.stringify({ name }),
  })
}
