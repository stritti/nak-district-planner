import { apiFetch } from './client'

export type CalendarType = 'ICS' | 'CALDAV' | 'GOOGLE' | 'MICROSOFT'
export type CalendarCapability = 'READ' | 'WRITE' | 'WEBHOOK'

export interface CalendarIntegrationResponse {
  id: string
  district_id: string
  congregation_id: string | null
  name: string
  type: CalendarType
  sync_interval: number
  capabilities: CalendarCapability[]
  is_active: boolean
  last_synced_at: string | null
  created_at: string
  updated_at: string
}

export interface CalendarIntegrationListResponse {
  items: CalendarIntegrationResponse[]
  total: number
}

export interface SyncResult {
  integration_id: string
  created: number
  updated: number
  cancelled: number
}

export function listIntegrations(districtId?: string): Promise<CalendarIntegrationListResponse> {
  const params = districtId ? `?district_id=${districtId}` : ''
  return apiFetch(`/api/v1/calendar-integrations${params}`)
}

export function createIntegration(payload: {
  district_id: string
  congregation_id?: string | null
  name: string
  type: CalendarType
  credentials: Record<string, string>
  sync_interval: number
  capabilities: CalendarCapability[]
}): Promise<CalendarIntegrationResponse> {
  return apiFetch('/api/v1/calendar-integrations', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function triggerSync(integrationId: string): Promise<SyncResult> {
  return apiFetch(`/api/v1/calendar-integrations/${integrationId}/sync`, { method: 'POST' })
}

export function updateIntegration(
  integrationId: string,
  payload: {
    name?: string
    credentials?: Record<string, string>
    sync_interval?: number
    capabilities?: CalendarCapability[]
  },
): Promise<CalendarIntegrationResponse> {
  return apiFetch(`/api/v1/calendar-integrations/${integrationId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteIntegration(integrationId: string): Promise<void> {
  return apiFetch(`/api/v1/calendar-integrations/${integrationId}`, { method: 'DELETE' })
}
