import { apiFetch } from './client'

export interface NotificationItem {
  id: string
  district_id: string
  congregation_id: string | null
  type: string
  title: string
  body: string
  payload: Record<string, unknown>
  read_at: string | null
  created_at: string
}

export interface NotificationListResponse {
  items: NotificationItem[]
  total: number
  limit: number
  offset: number
}

export interface UnreadCountResponse {
  count: number
}

export function listNotifications(
  districtId: string,
  options?: { unreadOnly?: boolean; limit?: number; offset?: number },
): Promise<NotificationListResponse> {
  const params = new URLSearchParams()
  if (options?.unreadOnly) params.append('unread_only', 'true')
  if (options?.limit) params.append('limit', String(options.limit))
  if (options?.offset) params.append('offset', String(options.offset))
  const qs = params.toString()
  return apiFetch<NotificationListResponse>(
    `/api/v1/notifications/${districtId}${qs ? `?${qs}` : ''}`,
  )
}

export function getUnreadCount(districtId: string): Promise<UnreadCountResponse> {
  return apiFetch<UnreadCountResponse>(`/api/v1/notifications/${districtId}/unread-count`)
}

export function markNotificationRead(notificationId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/notifications/${notificationId}/read`, { method: 'POST' })
}

export function markAllNotificationsRead(districtId: string): Promise<{ marked_read: number }> {
  return apiFetch<{ marked_read: number }>(`/api/v1/notifications/${districtId}/read-all`, {
    method: 'POST',
  })
}
