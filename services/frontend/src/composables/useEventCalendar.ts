// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
//     SPDX-License-Identifier: AGPL-3.0-only

import { computed, type Ref } from 'vue'
import type { EventResponse } from '../api/events'

export const WEEKDAY_SHORT = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa']
export const MONTH_NAMES = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
  'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']

export function localDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function startOfWeek(d: Date): Date {
  const r = new Date(d)
  const dow = r.getDay()
  r.setDate(r.getDate() - (dow === 0 ? 6 : dow - 1)) // Monday
  return r
}

export function monthRange(offset: number) {
  const now = new Date()
  return {
    from: localDate(new Date(now.getFullYear(), now.getMonth() + offset, 1)),
    to: localDate(new Date(now.getFullYear(), now.getMonth() + offset + 1, 0)),
  }
}

export function useEventCalendar(viewMode: Ref<'list' | 'week' | 'month'>, currentPeriodStart: Ref<Date>, calendarEvents: Ref<EventResponse[]>) {
  const weekDays = computed(() => {
    const today = localDate(new Date())
    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date(currentPeriodStart.value)
      d.setDate(d.getDate() + i)
      return {
        iso: localDate(d),
        day: d.getDate(),
        weekdayShort: WEEKDAY_SHORT[d.getDay()],
        isToday: localDate(d) === today,
      }
    })
  })

  const calendarDays = computed(() => {
    const year = currentPeriodStart.value.getFullYear()
    const month = currentPeriodStart.value.getMonth()
    const firstDay = new Date(year, month, 1)
    const dow = firstDay.getDay()
    const start = new Date(firstDay)
    start.setDate(start.getDate() - (dow === 0 ? 6 : dow - 1))
    const today = localDate(new Date())
    return Array.from({ length: 42 }, (_, i) => {
      const d = new Date(start)
      d.setDate(d.getDate() + i)
      return {
        iso: localDate(d),
        day: d.getDate(),
        currentMonth: d.getMonth() === month,
        isToday: localDate(d) === today,
      }
    })
  })

  const eventsByDate = computed(() => {
    const map: Record<string, EventResponse[]> = {}
    for (const event of calendarEvents.value) {
      const key = event.start_at.slice(0, 10)
      if (!map[key]) map[key] = []
      map[key].push(event)
    }
    for (const key in map) {
      map[key].sort((a, b) => a.start_at.localeCompare(b.start_at))
    }
    return map
  })

  // Feiertage separat, damit sie im Spaltenkopf erscheinen (nicht im Event-Bereich)
  const calendarHolidays = computed(() => {
    const map: Record<string, string[]> = {}
    for (const event of calendarEvents.value) {
      if (event.category === 'Feiertag') {
        const key = event.start_at.slice(0, 10)
        if (!map[key]) map[key] = []
        map[key].push(event.title)
      }
    }
    return map
  })

  const periodLabel = computed(() => {
    if (viewMode.value === 'week' && weekDays.value.length) {
      const s = weekDays.value[0].iso
      const e = weekDays.value[6].iso
      const fmt = (iso: string) => iso.slice(8) + '.' + iso.slice(5, 7) + '.'
      return `${fmt(s)} – ${fmt(e)}${e.slice(0, 4)}`
    }
    const m = currentPeriodStart.value.getMonth()
    const y = currentPeriodStart.value.getFullYear()
    return `${MONTH_NAMES[m]} ${y}`
  })

  return { weekDays, calendarDays, eventsByDate, calendarHolidays, periodLabel }
}
