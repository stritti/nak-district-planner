// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import type { LeaderResponse, LeaderUpdate } from '../../api/leaders'

/** Fields stored on the person itself (PATCH .../inline). */
export type InlineLeaderField = 'name' | 'email' | 'phone' | 'rank' | 'is_active'

/** Cell kinds: the person's fields plus the role, which belongs to one assignment. */
export type InlineCellField = InlineLeaderField | 'special_role'

/** Fields whose change is a lifecycle decision and needs the district admin role. */
export const LIFECYCLE_FIELDS: readonly InlineCellField[] = ['is_active']

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
    default:
      return { [field]: value || null } as Pick<LeaderUpdate, InlineLeaderField>
  }
}

/** Current stored value of a person field as the cell's string draft representation. */
export function inlineLeaderValue(leader: LeaderResponse, field: InlineLeaderField): string {
  const value = leader[field]
  return value === null || value === undefined ? '' : String(value)
}
