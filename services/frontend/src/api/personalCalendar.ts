// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { apiFetch } from './client'
export interface PersonalEvent { planning_slot_id: string; uid: string; title: string; start_at: string; end_at: string; status: string; duties: string[]; congregation_id: string | null }
export interface PersonalToken { id: string; token: string; label: string }
export function listPersonalEvents(district: string, from: string, to: string): Promise<PersonalEvent[]> {
 return apiFetch(`/api/v1/personal-calendar/events?${new URLSearchParams({ district_id: district, from_date: from, to_date: to })}`)
}
export function listPersonalTokens(district: string, subject: string): Promise<PersonalToken[]> {
 return apiFetch(`/api/v1/export-tokens?${new URLSearchParams({ district_id: district, subject_sub: subject })}`)
}
export function createPersonalToken(district: string, subject: string): Promise<PersonalToken> {
 return apiFetch('/api/v1/export-tokens', { method: 'POST', body: JSON.stringify({ district_id: district, subject_sub: subject, token_type: 'INTERNAL', label: 'Mein Kalender' }) })
}
export function revokePersonalToken(id: string): Promise<void> { return apiFetch(`/api/v1/export-tokens/${encodeURIComponent(id)}`, { method: 'DELETE' }) }
