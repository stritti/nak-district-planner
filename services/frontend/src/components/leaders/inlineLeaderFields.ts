// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import type { LeaderResponse, LeaderUpdate } from '../../api/leaders'

export type InlineLeaderField =
  | 'name'
  | 'email'
  | 'phone'
  | 'rank'
  | 'special_role'
  | 'congregation_id'
  | 'is_active'

/** Fields whose change is a lifecycle decision and needs the district admin role. */
export const LIFECYCLE_FIELDS: readonly InlineLeaderField[] = ['is_active']

/** Cell draft (always a string) -> inline PATCH body for exactly this field. */
export function inlineLeaderPayload(
  field: InlineLeaderField,
  value: string,
): Pick<LeaderUpdate, InlineLeaderField> {
  switch (field) {
    case 'is_active':
      return { is_active: value === 'true' }
    case 'rank':
      return { rank: value as NonNullable<LeaderUpdate['rank']> }
    case 'special_role':
      return { special_role: (value || null) as LeaderUpdate['special_role'] }
    case 'congregation_id':
      return { congregation_id: value || null }
    default:
      return { [field]: value || null } as Pick<LeaderUpdate, InlineLeaderField>
  }
}

/** Current stored value of a field as the cell's string draft representation. */
export function inlineLeaderValue(leader: LeaderResponse, field: InlineLeaderField): string {
  const value = leader[field]
  return value === null || value === undefined ? '' : String(value)
}
