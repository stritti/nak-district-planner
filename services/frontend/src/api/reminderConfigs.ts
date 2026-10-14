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

export function updateReminderConfig(
  districtId: string,
  configId: string,
  input: Partial<ReminderConfigInput>,
): Promise<ReminderConfig> {
  return apiFetch(`${baseUrl(districtId)}/${encodeURIComponent(configId)}`, {
    method: 'PUT',
    body: JSON.stringify(input),
  })
}

export function deleteReminderConfig(districtId: string, configId: string): Promise<void> {
  return apiFetch(`${baseUrl(districtId)}/${encodeURIComponent(configId)}`, { method: 'DELETE' })
}
