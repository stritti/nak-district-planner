// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import type { CongregationResponse } from '../api/districts'
import type { MatrixResponse } from '../api/matrix'

/** What the start page knows about the selected district; `null` = not loaded or not readable. */
export interface GettingStartedFacts {
  districtCount: number
  congregations: CongregationResponse[] | null
  leaderCount: number | null
  matrix: MatrixResponse | null
  exportTokenCount: number | null
}

export interface GettingStartedPermissions {
  /** May create districts (superadmin). */
  createDistrict: boolean
  /** District admin: congregations, leaders and calendar subscriptions. */
  adminDistrict: boolean
  /** Planner: drafts, assignments and release. */
  planDistrict: boolean
}

export type StepState = 'done' | 'open' | 'unknown'

export interface GettingStartedStep {
  id: 'district' | 'congregations' | 'leaders' | 'drafts' | 'assign' | 'release' | 'subscribe'
  title: string
  state: StepState
  /** Current status in one sentence. */
  detail: string
  to: string
  /** Button text when the user may take the step; otherwise `hint` says who does. */
  actionLabel: string | null
  hint: string | null
}

export const GETTING_STARTED_WEEKS = 4

interface ServiceCounts {
  services: number
  gaps: number
  unreleased: number
}

function countServices(matrix: MatrixResponse): ServiceCounts {
  const counts = { services: 0, gaps: 0, unreleased: 0 }
  for (const row of matrix.rows) {
    for (const cell of Object.values(row.cells)) {
      if (!cell.event_id) continue
      if (cell.category !== 'Gottesdienst') continue
      counts.services += 1
      if (cell.is_gap) counts.gaps += 1
      if (cell.approval_status !== 'CONFIRMED') counts.unreleased += 1
    }
  }
  return counts
}

function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`
}

function action(allowed: boolean, label: string, who: string): Pick<GettingStartedStep, 'actionLabel' | 'hint'> {
  return allowed ? { actionLabel: label, hint: null } : { actionLabel: null, hint: who }
}

const ADMIN_HINT = 'Diesen Schritt übernimmt ein Bezirksadmin.'
const PLANNER_HINT = 'Diesen Schritt übernimmt die Planung des Bezirks.'

/** The seven steps from an empty installation to a calendar subscription, in order. */
export function gettingStartedSteps(
  facts: GettingStartedFacts,
  can: GettingStartedPermissions,
): GettingStartedStep[] {
  const congregations = facts.congregations
  const withTimes = congregations?.filter((c) => c.service_times.length > 0).length ?? 0
  const counts = facts.matrix ? countServices(facts.matrix) : null
  const range = `in den nächsten ${GETTING_STARTED_WEEKS} Wochen`

  const steps: GettingStartedStep[] = [
    {
      id: 'district',
      title: 'Bezirk anlegen',
      state: facts.districtCount > 0 ? 'done' : 'open',
      detail: facts.districtCount > 0
        ? plural(facts.districtCount, 'Bezirk angelegt.', 'Bezirke angelegt.')
        : 'Noch kein Bezirk angelegt.',
      to: '/admin/districts',
      ...action(can.createDistrict, 'Bezirk anlegen', 'Bezirke legt ein Superadmin an.'),
    },
    {
      id: 'congregations',
      title: 'Gemeinden und Gottesdienstzeiten erfassen',
      state: congregations === null
        ? 'unknown'
        : congregations.length > 0 && withTimes === congregations.length ? 'done' : 'open',
      detail: congregations === null
        ? 'Gemeinden konnten nicht geladen werden.'
        : congregations.length === 0
          ? 'Noch keine Gemeinde angelegt.'
          : `${withTimes} von ${plural(congregations.length, 'Gemeinde hat', 'Gemeinden haben')} Gottesdienstzeiten.`,
      to: '/admin/districts',
      ...action(can.adminDistrict, 'Gemeinden bearbeiten', ADMIN_HINT),
    },
    {
      id: 'leaders',
      title: 'Amtsträger erfassen',
      state: facts.leaderCount === null ? 'unknown' : facts.leaderCount > 0 ? 'done' : 'open',
      detail: facts.leaderCount === null
        ? 'Amtsträger konnten nicht geladen werden.'
        : facts.leaderCount === 0
          ? 'Noch keine Amtsträger erfasst.'
          : `${plural(facts.leaderCount, 'Amtsträger', 'Amtsträger')} erfasst.`,
      to: '/admin/leaders',
      ...action(can.adminDistrict, 'Amtsträger erfassen', ADMIN_HINT),
    },
    {
      id: 'drafts',
      title: 'Gottesdienste als Entwürfe erzeugen',
      state: counts === null ? 'unknown' : counts.services > 0 ? 'done' : 'open',
      detail: counts === null
        ? 'Die Planung konnte nicht geladen werden.'
        : counts.services > 0
          ? `${plural(counts.services, 'Gottesdienst', 'Gottesdienste')} ${range} geplant.`
          : `Noch keine Gottesdienste ${range}.`,
      to: '/matrix',
      ...action(can.planDistrict, 'Zur Matrix', PLANNER_HINT),
    },
    {
      id: 'assign',
      title: 'Dienstleiter zuweisen',
      state: counts === null ? 'unknown' : counts.services > 0 && counts.gaps === 0 ? 'done' : 'open',
      detail: counts === null
        ? 'Die Planung konnte nicht geladen werden.'
        : counts.services === 0
          ? 'Erst sind Gottesdienste nötig.'
          : counts.gaps === 0
            ? `Alle Gottesdienste ${range} haben einen Dienstleiter.`
            : `${plural(counts.gaps, 'Lücke', 'Lücken')} ${range}.`,
      to: '/matrix',
      ...action(can.planDistrict, 'Lücken schließen', PLANNER_HINT),
    },
    {
      id: 'release',
      title: 'Planung freigeben',
      state: counts === null
        ? 'unknown'
        : counts.services > 0 && counts.unreleased === 0 ? 'done' : 'open',
      detail: counts === null
        ? 'Die Planung konnte nicht geladen werden.'
        : counts.services === 0
          ? 'Erst sind Gottesdienste nötig.'
          : `${counts.services - counts.unreleased} von ${plural(counts.services, 'Gottesdienst', 'Gottesdiensten')} ${range} freigegeben.`,
      to: '/matrix',
      ...action(can.planDistrict, 'Zur Freigabe', PLANNER_HINT),
    },
    {
      id: 'subscribe',
      title: 'Kalender-Abo bereitstellen',
      state: facts.exportTokenCount === null ? 'unknown' : facts.exportTokenCount > 0 ? 'done' : 'open',
      detail: facts.exportTokenCount === null
        ? 'Kalender-Abos sieht nur ein Bezirksadmin.'
        : facts.exportTokenCount > 0
          ? `${plural(facts.exportTokenCount, 'Kalender-Abo', 'Kalender-Abos')} eingerichtet.`
          : 'Noch kein Kalender-Abo eingerichtet.',
      to: '/admin/export',
      ...action(can.adminDistrict, 'Abo einrichten', ADMIN_HINT),
    },
  ]
  return steps
}

/** The first step that is not done yet, or `null` when everything is set up. */
export function nextStepId(steps: GettingStartedStep[]): GettingStartedStep['id'] | null {
  return steps.find((step) => step.state === 'open')?.id ?? null
}
