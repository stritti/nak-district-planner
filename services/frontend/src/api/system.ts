import { apiFetch } from './client'

export interface SystemVersionResponse {
  current_version: string
  latest_version: string | null
  last_checked: number | null
  release_url: string | null
}

export interface UpdateResponse {
  status: 'manual' | 'started' | 'ok' | 'error'
  mode: 'manual' | 'docker-socket'
  instructions: string[] | null
}

export function getVersion(refresh = false): Promise<SystemVersionResponse> {
  const qs = refresh ? '?refresh=true' : ''
  return apiFetch(`/api/v1/system/version${qs}`)
}

export function triggerUpdate(): Promise<UpdateResponse> {
  return apiFetch('/api/v1/system/update', { method: 'POST' })
}
