// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import type { EventResponse } from '../api/events'
import { localDate, monthRange, startOfWeek, useEventCalendar } from './useEventCalendar'

function event(overrides: Partial<EventResponse>): EventResponse {
  return {
    id: 'e',
    title: 'Gottesdienst',
    description: null,
    start_at: '2026-03-01T10:00:00',
    end_at: '2026-03-01T11:00:00',
    district_id: 'd',
    congregation_id: null,
    category: 'Gottesdienst',
    is_service: true,
    source: 'INTERNAL',
    status: 'ACTIVE',
    approval_status: null,
    visibility: 'INTERNAL',
    applicability: [],
    created_at: '2026-01-01T00:00:00',
    updated_at: '2026-01-01T00:00:00',
    ...overrides,
  } as EventResponse
}

describe('date helpers', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 2, 15, 12))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('formats local dates with zero padding', () => {
    expect(localDate(new Date(2026, 0, 5))).toBe('2026-01-05')
  })

  it.each([
    [new Date(2026, 2, 4), '2026-03-02'], // Wednesday
    [new Date(2026, 2, 2), '2026-03-02'], // Monday
    [new Date(2026, 2, 8), '2026-03-02'], // Sunday belongs to the previous week
  ])('startOfWeek(%o) is Monday %s', (date, expected) => {
    expect(localDate(startOfWeek(date))).toBe(expected)
  })

  it('computes month ranges relative to today', () => {
    expect(monthRange(0)).toEqual({ from: '2026-03-01', to: '2026-03-31' })
    expect(monthRange(-1)).toEqual({ from: '2026-02-01', to: '2026-02-28' })
  })
})

describe('useEventCalendar', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 2, 4, 12))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('builds a week with today marked and a week label', () => {
    const cal = useEventCalendar(ref('week'), ref(new Date(2026, 2, 2)), ref([]))

    expect(cal.weekDays.value.map(d => d.weekdayShort)).toEqual(['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'])
    expect(cal.weekDays.value.filter(d => d.isToday).map(d => d.iso)).toEqual(['2026-03-04'])
    expect(cal.periodLabel.value).toBe('02.03. – 08.03.2026')
  })

  it('pads a month starting on Sunday back to the previous Monday', () => {
    // 1 March 2026 is a Sunday
    const cal = useEventCalendar(ref('month'), ref(new Date(2026, 2, 1)), ref([]))
    const days = cal.calendarDays.value

    expect(days).toHaveLength(42)
    expect(days[0]).toMatchObject({ iso: '2026-02-23', currentMonth: false })
    expect(days[6]).toMatchObject({ iso: '2026-03-01', currentMonth: true })
    expect(days.filter(d => d.isToday).map(d => d.iso)).toEqual(['2026-03-04'])
    expect(cal.periodLabel.value).toBe('März 2026')
  })

  it('pads a month starting mid-week back to Monday', () => {
    // 1 April 2026 is a Wednesday
    const cal = useEventCalendar(ref('month'), ref(new Date(2026, 3, 1)), ref([]))

    expect(cal.calendarDays.value[0].iso).toBe('2026-03-30')
    expect(cal.calendarDays.value[2]).toMatchObject({ iso: '2026-04-01', currentMonth: true })
  })

  it('uses the month label in list mode', () => {
    const cal = useEventCalendar(ref('list'), ref(new Date(2026, 11, 1)), ref([]))

    expect(cal.periodLabel.value).toBe('Dezember 2026')
  })

  it('groups events per day sorted by start time and collects holidays separately', () => {
    const events = ref([
      event({ id: 'late', start_at: '2026-03-04T19:00:00' }),
      event({ id: 'early', start_at: '2026-03-04T09:30:00' }),
      event({ id: 'other', start_at: '2026-03-05T10:00:00', category: null }),
      event({ id: 'h1', title: 'Karfreitag', start_at: '2026-04-03T00:00:00', category: 'Feiertag' }),
      event({ id: 'h2', title: 'Zusatz', start_at: '2026-04-03T00:00:00', category: 'Feiertag' }),
    ])
    const cal = useEventCalendar(ref('month'), ref(new Date(2026, 2, 1)), events)

    expect(cal.eventsByDate.value['2026-03-04'].map(e => e.id)).toEqual(['early', 'late'])
    expect(cal.eventsByDate.value['2026-03-05'].map(e => e.id)).toEqual(['other'])
    expect(cal.calendarHolidays.value).toEqual({ '2026-04-03': ['Karfreitag', 'Zusatz'] })
  })
})
