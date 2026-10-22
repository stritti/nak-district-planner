// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

// Pure rules about the role of an assignment; kept apart from the HTTP calls so that
// they stay available when a test replaces `./leaders` with mocks.

export const SPECIAL_ROLES = [
  { value: 'Gemeindevorsteher', label: 'Gemeindevorsteher' },
  { value: 'Bezirksvorsteher',  label: 'Bezirksvorsteher' },
] as const

export type SpecialRole = (typeof SPECIAL_ROLES)[number]['value']

/** A congregation leader serves a congregation, a district leader the district level. */
export function roleFitsLevel(role: SpecialRole | null, congregationId: string | null): boolean {
  if (role === 'Gemeindevorsteher') return congregationId !== null
  if (role === 'Bezirksvorsteher') return congregationId === null
  return true
}

/** The roles that may be given on this level (congregation id, or null for the district level). */
export function roleChoicesFor(congregationId: string | null) {
  return SPECIAL_ROLES.filter((role) => roleFitsLevel(role.value, congregationId))
}
