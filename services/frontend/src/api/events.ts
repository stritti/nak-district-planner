import { apiFetch } from './client'

export interface EventResponse {
  id: string
  title: string
  description: string | null
  start_at: string
  end_at: string
  district_id: string
  congregation_id: string | null
  category: string | null
  source: 'INTERNAL' | 'EXTERNAL'
  status: 'DRAFT' | 'PUBLISHED' | 'CANCELLED'
  visibility: 'INTERNAL' | 'PUBLIC'
  audiences: string[]
  applicability: string[]
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
  status?: string
  from_dt?: string
  to_dt?: string
  limit?: number
  offset?: number
}

export interface EventUpdate {
  district_id?: string
  congregation_id?: string | null
  status?: string
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
  if (params.district_id !== undefined && params.district_id !== null) {
    query.set('district_id', params.district_id)
  }
  if (params.congregation_id !== undefined && params.congregation_id !== null) {
    query.set('congregation_id', params.congregation_id)
  }
  if (params.group_id !== undefined && params.group_id !== null) {
    query.set('group_id', params.group_id)
  }
  if (params.only_district_level === true) {
    query.set('only_district_level', 'true')
  }
  if (params.status !== undefined && params.status !== null) {
    query.set('status', params.status)
  }
  if (params.from_dt !== undefined && params.from_dt !== null) {
    query.set('from_dt', params.from_dt)
  }
  if (params.to_dt !== undefined && params.to_dt !== null) {
    query.set('to_dt', params.to_dt)
  }
  if (params.limit !== undefined && params.limit !== null) {
    query.set('limit', String(params.limit))
  }
  if (params.offset !== undefined && params.offset !== null) {
    query.set('offset', String(params.offset))
  }
  const qs = query.toString()
  return apiFetch(`/api/v1/events${qs ? '?' + qs : ''}`)
}