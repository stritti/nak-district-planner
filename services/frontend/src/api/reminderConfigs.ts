// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { apiFetch } from './client'

export type RecipientRole = 'DISTRICT_ADMIN' | 'CONGREGATION_ADMIN' | 'PLANNER' | 'VIEWER'

export interface ReminderConfigInput {
  day_of_month: number
  time_of_day: string
  subject_template: string
  body_template: string
  recipient_role: RecipientRole
  is_active: boolean
}

export interface ReminderConfig extends ReminderConfigInput {
  id: string
  district_id: string
  created_at: string
  updated_at: string
  revision: string
}

const baseUrl = (districtId: string) => `/api/v1/districts/${encodeURIComponent(districtId)}/reminder-configs`

export function listReminderConfigs(districtId: string): Promise<ReminderConfig[]> {
  return apiFetch(baseUrl(districtId))
}

export function createReminderConfig(districtId: string, input: ReminderConfigInput): Promise<ReminderConfig> {
  return apiFetch(baseUrl(districtId), {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

const missingRevision = () => Promise.reject(new Error('Versionsinformation fehlt. Bitte neu laden.'))

export function updateReminderConfig(
  districtId: string,
  configId: string,
  input: Partial<ReminderConfigInput>,
  revision: string,
): Promise<ReminderConfig> {
  if (!revision) return missingRevision()
  return apiFetch(`${baseUrl(districtId)}/${encodeURIComponent(configId)}`, {
    method: 'PUT',
    headers: { 'If-Match': revision },
    body: JSON.stringify(input),
  })
}

/** Soft-deactivates; the response is the updated record with its new revision. */
export function deleteReminderConfig(
  districtId: string,
  configId: string,
  revision: string,
): Promise<ReminderConfig> {
  if (!revision) return missingRevision()
  return apiFetch(`${baseUrl(districtId)}/${encodeURIComponent(configId)}`, {
    method: 'DELETE',
    headers: { 'If-Match': revision },
  })
}
