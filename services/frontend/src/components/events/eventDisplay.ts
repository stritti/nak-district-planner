// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import type { EventResponse } from '../../api/events'

export interface CalendarDay {
  iso: string
  day: number
  isToday: boolean
  weekdayShort?: string
  currentMonth?: boolean
}

/** "HH:MM" for an ISO timestamp, empty for midnight (all-day style events). */
export function formatTime(iso: string): string {
  const d = new Date(iso)
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return h === '00' && m === '00' ? '' : `${h}:${m}`
}

export function eventPillClass(event: EventResponse): string {
  if (event.category === 'Feiertag')   return 'bg-amber-100 text-amber-800'
  if (event.status === 'CANCELLED')    return 'bg-red-100 text-red-600 line-through'
  if (event.is_service)                return 'bg-blue-100 text-blue-800'
  return 'bg-gray-100 text-gray-700'
}

/** Events of a day without public holidays (those are rendered separately). */
export function regularEvents(events: EventResponse[] | undefined): EventResponse[] {
  return (events ?? []).filter((e) => e.category !== 'Feiertag')
}
