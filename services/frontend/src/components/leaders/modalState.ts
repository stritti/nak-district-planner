// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import type { LeaderAssignment, LeaderRank, SpecialRole } from '../../api/leaders'

/** Form state shapes for the leader administration modals (owned by the parent view). */
export interface ApproveModalState {
  open: boolean
  registrationId: string
  name: string
  email: string
  role: 'DISTRICT_ADMIN' | 'CONGREGATION_ADMIN' | 'PLANNER' | 'VIEWER'
  scope_type: 'DISTRICT' | 'CONGREGATION'
  rank: string | null
  congregation_id: string | null
  special_role: string | null
  error: string
}

export interface RejectModalState {
  open: boolean
  registrationId: string
  name: string
  reason: string
  error: string
}

export interface AddModalState {
  open: boolean
  congregationId: string | null
  name: string
  rank: LeaderRank | ''
  special_role: SpecialRole | null
  email: string
  phone: string
  error: string
  /** Same-named people the server reported; non-empty means a confirmation is pending. */
  duplicates: { id: string; label: string }[]
}

export interface EditModalState {
  open: boolean
  leaderId: string
  revision: string
  name: string
  rank: LeaderRank | ''
  /** Assignments as last loaded; they are changed through their own requests, not by "Speichern". */
  assignments: LeaderAssignment[]
  /** Draft of the assignment about to be added; `target` is '' (none), 'district' or a congregation id. */
  newAssignment: { target: string; role: SpecialRole | null }
  email: string
  phone: string
  notes: string
  is_active: boolean
  hidden_from_lists: boolean
  service_end_date: string
  error: string
}

export interface ExportModalState {
  open: boolean
  leaderId: string
  leaderName: string
  leaderRank: string
  icsUrl: string
  error: string
}
