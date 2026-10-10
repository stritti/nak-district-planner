// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, expect, it } from 'vitest'
import { HELP_CATALOG, resolveHelp, resolveHelpRole, type HelpAccess } from './catalog'

const guest: HelpAccess = { authenticated: false, memberships: [] }
const viewer: HelpAccess = { authenticated: true, memberships: [{ role: 'VIEWER' }], accessStatus: 'ACTIVE' }
const planner: HelpAccess = { authenticated: true, memberships: [{ role: 'PLANNER' }], accessStatus: 'ACTIVE' }

describe('contextual help catalog and role resolution', () => {
  it('has stable and unique IDs', () => {
    expect(new Set(HELP_CATALOG.map(({ help_id }) => help_id)).size).toBe(HELP_CATALOG.length)
  })
  it('shows guest content only on public pages', () => {
    expect(resolveHelp('login', guest).map(({ help_id }) => help_id)).toEqual(['guest-sign-in'])
    expect(resolveHelp('registration', guest).map(({ help_id }) => help_id)).toEqual(['guest-registration'])
    expect(resolveHelp('events', guest)).toEqual([])
    expect(resolveHelp('matrix', guest)).toEqual([])
  })
  it('shows viewer content but never planner or guest content', () => {
    expect(resolveHelpRole(viewer)).toBe('viewer')
    expect(resolveHelp('events', viewer).map(({ help_id }) => help_id)).toEqual(['viewer-events'])
    expect(resolveHelp('matrix', viewer)).toEqual([])
    expect(resolveHelp('login', viewer)).toEqual([])
  })
  it('shows planning guidance in the events and matrix contexts', () => {
    expect(resolveHelp('events', planner).map(({ help_id }) => help_id)).toEqual(['planner-events'])
    expect(resolveHelp('matrix', planner).map(({ help_id }) => help_id)).toEqual(['planner-matrix'])
  })
  it('prioritizes planning permissions for multiple roles and administrators', () => {
    expect(resolveHelpRole({ ...viewer, memberships: [{ role: 'VIEWER' }, { role: 'DISTRICT_ADMIN' }] })).toBe('planner')
    expect(resolveHelpRole({ authenticated: true, memberships: [], isSuperadmin: true, accessStatus: 'ACTIVE' })).toBe('planner')
  })
  it('fails closed for unknown and pending authenticated roles', () => {
    expect(resolveHelp('events', { authenticated: true, memberships: [{ role: 'UNRELATED' }], accessStatus: 'ACTIVE' })).toEqual([])
    expect(resolveHelp('events', { ...planner, accessStatus: 'PENDING_APPROVAL' })).toEqual([])
    expect(resolveHelp('events', { authenticated: true, memberships: [] })).toEqual([])
  })
})
