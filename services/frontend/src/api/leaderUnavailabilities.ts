// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { apiFetch } from './client'

export type UnavailabilityReason = 'URLAUB' | 'SPERRZEIT' | 'FORTBILDUNG' | 'SONSTIGES'

export const UNAVAILABILITY_REASONS: { value: UnavailabilityReason; label: string }[] = [
  { value: 'URLAUB', label: 'Urlaub' },
  { value: 'SPERRZEIT', label: 'Sperrzeit' },
  { value: 'FORTBILDUNG', label: 'Fortbildung' },
  { value: 'SONSTIGES', label: 'Sonstiges' },
]

export function unavailabilityReasonLabel(reason: UnavailabilityReason): string {
  return UNAVAILABILITY_REASONS.find((r) => r.value === reason)?.label ?? reason
}

export const PLANNING_TIMEZONE = 'Europe/Berlin'

const OFFSET_ITERATION_LIMIT = 3

export function planningDayBounds(date: string): { start: string; end: string } {
  const [year, month, day] = date.split('-').map(Number)
  if (!year || !month || !day) throw new Error('Ungültiges Datum.')

  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: PLANNING_TIMEZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hourCycle: 'h23',
  })

  const offsetAt = (utcMs: number) => {
    const parts = Object.fromEntries(
      formatter.formatToParts(new Date(utcMs)).map((part) => [part.type, part.value]),
    )
    const zonedAsUtc = Date.UTC(
      Number(parts.year),
      Number(parts.month) - 1,
      Number(parts.day),
      Number(parts.hour),
      Number(parts.minute),
      Number(parts.second),
    )
    return zonedAsUtc - utcMs
  }

  const localMidnightUtcMs = (y: number, m: number, d: number) => {
    let guess = Date.UTC(y, m, d)
    for (let i = 0; i < OFFSET_ITERATION_LIMIT; i++) {
      const next = Date.UTC(y, m, d) - offsetAt(guess)
      if (next === guess) return guess
      guess = next
    }
    return guess
  }

  const startMs = localMidnightUtcMs(year, month - 1, day)
  const nextDayStartMs = localMidnightUtcMs(year, month - 1, day + 1)
  return { start: new Date(startMs).toISOString(), end: new Date(nextDayStartMs - 1).toISOString() }
}

export function formatUnavailabilityPeriod(item: LeaderUnavailabilityResponse): string {
  const locale = 'de-DE'
  const format = (value: string) =>
    new Date(value).toLocaleDateString(locale, { timeZone: PLANNING_TIMEZONE })
  const start = format(item.start_at)
  const end = format(item.end_at)
  return start === end ? start : `${start} – ${end}`
}

export interface LeaderUnavailabilityResponse {
  id: string
  leader_id: string
  start_at: string
  end_at: string
  reason: UnavailabilityReason
  note: string | null
  created_at: string
  updated_at: string
}

export interface LeaderUnavailabilityCreate {
  leader_id: string
  start_at: string
  end_at: string
  reason: UnavailabilityReason
  note?: string | null
}

export function listUnavailabilities(
  districtId: string,
  leaderId?: string,
): Promise<LeaderUnavailabilityResponse[]> {
  const query = leaderId ? `?leader_id=${encodeURIComponent(leaderId)}` : ''
  return apiFetch<LeaderUnavailabilityResponse[]>(
    `/api/v1/districts/${districtId}/leader-unavailabilities${query}`,
  )
}

export function createUnavailability(
  districtId: string,
  body: LeaderUnavailabilityCreate,
): Promise<LeaderUnavailabilityResponse> {
  return apiFetch<LeaderUnavailabilityResponse>(
    `/api/v1/districts/${districtId}/leader-unavailabilities`,
    {
      method: 'POST',
      body: JSON.stringify(body),
    },
  )
}

export function deleteUnavailability(districtId: string, unavailabilityId: string): Promise<void> {
  return apiFetch<void>(
    `/api/v1/districts/${districtId}/leader-unavailabilities/${unavailabilityId}`,
    {
      method: 'DELETE',
    },
  )
}
