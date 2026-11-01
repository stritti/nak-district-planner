// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, expect, it } from 'vitest'
import type { CongregationResponse } from '../api/districts'
import type { MatrixCell, MatrixResponse } from '../api/matrix'
import { gettingStartedSteps, nextStepId, type GettingStartedFacts } from './gettingStarted'

const congregation = (id: string, withTimes: boolean): CongregationResponse => ({
  id,
  name: id,
  district_id: 'd1',
  group_id: null,
  group_name: null,
  service_times: withTimes ? [{ weekday: 6, time: '09:30' }] : [],
  created_at: '',
  updated_at: '',
  revision: '"r"',
})

const cell = (overrides: Partial<MatrixCell>): MatrixCell => ({
  event_id: 'e', event_title: null, category: 'Gottesdienst', is_gap: false,
  assignment_id: null, assignment_status: null, leader_id: null, leader_name: null,
  approval_status: 'PLANNED', ...overrides,
})

const matrix = (cells: MatrixCell[]): MatrixResponse => ({
  dates: cells.map((_, index) => `2026-11-0${index + 1}`),
  rows: [{
    congregation_id: 'c1',
    congregation_name: 'Nord',
    cells: Object.fromEntries(cells.map((value, index) => [`2026-11-0${index + 1}`, value])),
  }],
  holidays: {},
})

const all = { createDistrict: true, adminDistrict: true, planDistrict: true }
const empty: GettingStartedFacts = {
  districtCount: 0, congregations: [], leaderCount: 0, matrix: matrix([]), exportTokenCount: 0,
}

function byId(facts: GettingStartedFacts, can = all) {
  return Object.fromEntries(gettingStartedSteps(facts, can).map((step) => [step.id, step]))
}

describe('gettingStartedSteps', () => {
  it('starts an empty installation at the district', () => {
    const steps = gettingStartedSteps(empty, all)
    expect(steps.map((step) => step.id)).toEqual([
      'district', 'congregations', 'leaders', 'drafts', 'assign', 'release', 'subscribe',
    ])
    expect(steps.every((step) => step.state === 'open')).toBe(true)
    expect(nextStepId(steps)).toBe('district')
    expect(steps[4].detail).toBe('Erst sind Gottesdienste nötig.')
    expect(steps[5].detail).toBe('Erst sind Gottesdienste nötig.')
  })

  it('counts congregations with service times, gaps and released services', () => {
    const steps = byId({
      districtCount: 2,
      congregations: [congregation('a', true), congregation('b', false)],
      leaderCount: 1,
      matrix: matrix([
        cell({ is_gap: true }),
        cell({ approval_status: 'CONFIRMED' }),
        cell({ category: 'Feiertag' }),
        cell({ event_id: null }),
      ]),
      exportTokenCount: 1,
    })
    expect(steps.district.detail).toBe('2 Bezirke angelegt.')
    expect(steps.congregations).toMatchObject({ state: 'open', detail: '1 von 2 Gemeinden haben Gottesdienstzeiten.' })
    expect(steps.leaders).toMatchObject({ state: 'done', detail: '1 Amtsträger erfasst.' })
    expect(steps.drafts).toMatchObject({ state: 'done', detail: '2 Gottesdienste in den nächsten 4 Wochen geplant.' })
    expect(steps.assign).toMatchObject({ state: 'open', detail: '1 Lücke in den nächsten 4 Wochen.' })
    expect(steps.release).toMatchObject({ state: 'open', detail: '1 von 2 Gottesdiensten in den nächsten 4 Wochen freigegeben.' })
    expect(steps.subscribe).toMatchObject({ state: 'done', detail: '1 Kalender-Abo eingerichtet.' })
  })

  it('is done once everything is set up', () => {
    const steps = gettingStartedSteps({
      districtCount: 1,
      congregations: [congregation('a', true)],
      leaderCount: 3,
      matrix: matrix([cell({ approval_status: 'CONFIRMED' })]),
      exportTokenCount: 2,
    }, all)
    expect(steps.every((step) => step.state === 'done')).toBe(true)
    expect(nextStepId(steps)).toBeNull()
    expect(steps[0].detail).toBe('1 Bezirk angelegt.')
    expect(steps[1].detail).toBe('1 von 1 Gemeinde hat Gottesdienstzeiten.')
    expect(steps[4].detail).toBe('Alle Gottesdienste in den nächsten 4 Wochen haben einen Dienstleiter.')
    expect(steps[6].detail).toBe('2 Kalender-Abos eingerichtet.')
  })

  it('marks facts that could not be loaded as unknown and skips them as next step', () => {
    const steps = gettingStartedSteps({
      districtCount: 1, congregations: null, leaderCount: null, matrix: null, exportTokenCount: null,
    }, all)
    expect(steps.slice(1).every((step) => step.state === 'unknown')).toBe(true)
    expect(steps[1].detail).toBe('Gemeinden konnten nicht geladen werden.')
    expect(steps[2].detail).toBe('Amtsträger konnten nicht geladen werden.')
    expect(steps[3].detail).toBe('Die Planung konnte nicht geladen werden.')
    expect(steps[6].detail).toBe('Kalender-Abos sieht nur ein Bezirksadmin.')
    expect(nextStepId(steps)).toBeNull()
  })

  it('does not claim completion when a day has several services', () => {
    const steps = byId({
      ...empty,
      districtCount: 1,
      matrix: matrix([cell({ approval_status: 'CONFIRMED', service_count: 2 })]),
    })
    expect(steps.drafts.detail).toBe('2 Gottesdienste in den nächsten 4 Wochen geplant.')
    expect(steps.assign).toMatchObject({ state: 'unknown', detail: 'An Tagen mit mehreren Gottesdiensten bitte in der Matrix prüfen.' })
    expect(steps.release.state).toBe('unknown')

    const withGap = byId({ ...empty, matrix: matrix([cell({ is_gap: true, service_count: 2 })]) })
    expect(withGap.assign).toMatchObject({ state: 'open', detail: '1 Lücke in den nächsten 4 Wochen.' })
    expect(withGap.release.detail).toBe('0 von 2 Gottesdiensten in den nächsten 4 Wochen freigegeben.')
  })

  it('offers each step only to the role that may take it', () => {
    const planner = byId(empty, { createDistrict: false, adminDistrict: false, planDistrict: true })
    expect(planner.district).toMatchObject({ actionLabel: null, hint: 'Bezirke legt ein Superadmin an.' })
    expect(planner.congregations.actionLabel).toBeNull()
    expect(planner.leaders.hint).toBe('Diesen Schritt übernimmt ein Bezirksadmin.')
    expect(planner.drafts).toMatchObject({ actionLabel: 'Zur Matrix', to: '/matrix', hint: null })
    expect(planner.subscribe.actionLabel).toBeNull()

    const viewer = byId(empty, { createDistrict: false, adminDistrict: false, planDistrict: false })
    expect(viewer.assign).toMatchObject({ actionLabel: null, hint: 'Diesen Schritt übernimmt die Planung des Bezirks.' })
  })
})
