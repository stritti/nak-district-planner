import { apiFetch } from './client'

export type PlanningSlotStatus = 'ACTIVE' | 'CANCELLED'
export type EventApprovalStatus = 'PLANNED' | 'CONFIRMED'
export type EventSource = 'INTERNAL' | 'EXTERNAL'
export type EventVisibility = 'INTERNAL' | 'PUBLIC'

export interface EventResponse {
  id: string
  title: string
  description: string | null
  start_at: string
  end_at: string
  district_id: string
  congregation_id: string | null
  category: string | null
  source: EventSource
  status: PlanningSlotStatus
  approval_status: EventApprovalStatus | null
  visibility: EventVisibility
  applicability: string[]
  invitation_source_congregation_id?: string | null
  invitation_source_event_id?: string | null
  created_at: string
  updated_at: string
}

export interface EventListResponse {
  items: EventResponse[]
  total: number
  limit: number
  offset: number
}

export interface EventListParams {
  district_id?: string
  congregation_id?: string
  group_id?: string
  only_district_level?: boolean
  status?: PlanningSlotStatus
  approval_status?: EventApprovalStatus
  from_dt?: string
  to_dt?: string
  limit?: number
  offset?: number
}

export interface EventUpdate {
  title?: string
  description?: string | null
  start_at?: string
  end_at?: string
  congregation_id?: string | null
  status?: PlanningSlotStatus
  approval_status?: EventApprovalStatus
  category?: string | null
}

export function updateEvent(id: string, data: EventUpdate): Promise<EventResponse> {
  return apiFetch(`/api/v1/events/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function listEvents(params: EventListParams = {}): Promise<EventListResponse> {
  const query = new URLSearchParams()
  if (params.district_id) query.set('district_id', params.district_id)
  if (params.congregation_id) query.set('congregation_id', params.congregation_id)
  if (params.group_id) query.set('group_id', params.group_id)
  if (params.only_district_level === true) query.set('only_district_level', 'true')
  if (params.status) query.set('status', params.status)
  if (params.approval_status) query.set('approval_status', params.approval_status)
  if (params.from_dt) query.set('from_dt', params.from_dt)
  if (params.to_dt) query.set('to_dt', params.to_dt)
  if (params.limit !== undefined) query.set('limit', String(params.limit))
  if (params.offset !== undefined) query.set('offset', String(params.offset))
  const qs = query.toString()
  return apiFetch(`/api/v1/events${qs ? '?' + qs : ''}`)
}

export interface BulkApprovalStatusRequest {
  year: number
  month: number
  approval_status: EventApprovalStatus
  congregation_id?: string | null
}

export interface BulkApprovalStatusResponse {
  updated_count: number
}

export function bulkUpdateApprovalStatus(
  districtId: string,
  data: BulkApprovalStatusRequest,
): Promise<BulkApprovalStatusResponse> {
  const query = districtId ? `?district_id=${districtId}` : ''
  return apiFetch(`/api/v1/events/bulk-approval-status${query}`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}
