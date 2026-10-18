// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { fetchMatrix, type MatrixCellConflict, type MatrixResponse } from '@/api/matrix'
import { useMatrixStore } from '@/stores/matrix'

vi.mock('@/api/matrix', () => ({ fetchMatrix: vi.fn() }))

const BLOCK: MatrixCellConflict = {
  rule_id: 'no_double_booking',
  severity: 'BLOCK',
  message: 'Doppelt belegt',
}
const WARN: MatrixCellConflict = {
  rule_id: 'travel_time_check',
  severity: 'WARN',
  message: 'Wechselzeit zu kurz',
}

function fixture(first: MatrixCellConflict[], second: MatrixCellConflict[]): MatrixResponse {
  const cell = (eventId: string, conflicts: MatrixCellConflict[]) => ({
    event_id: eventId,
    assignment_event_id: eventId,
    revision: '"before"',
    event_title: 'Gottesdienst',
    category: 'Gottesdienst',
    is_gap: false,
    assignment_id: 'assignment',
    assignment_status: 'ASSIGNED' as const,
    leader_id: 'old',
    leader_name: 'Alter Dienstleiter',
    conflicts,
  })
  return {
    dates: ['2026-10-18'],
    rows: [
      { congregation_id: 'north', congregation_name: 'Nord',
        cells: { '2026-10-18': cell('event-a', first) } },
      { congregation_id: 'south', congregation_name: 'Süd',
        cells: { '2026-10-18': cell('event-b', second) } },
    ],
    holidays: {},
  }
}

function setup() {
  const store = useMatrixStore()
  store.districtId = 'district'
  store.fromDt = '2026-10-18T00:00:00Z'
  store.toDt = '2026-10-18T23:59:59Z'
  store.matrix = fixture([BLOCK], [WARN])
  return store
}

const saved = {
  id: 'assignment-a',
  event_id: 'event-a',
  leader_id: 'new',
  leader_name: 'Neuer Dienstleiter',
  status: 'ASSIGNED' as const,
  created_at: '2026-10-18T10:00:00Z',
  updated_at: '2026-10-18T10:00:00Z',
  event_revision: '"after"',
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('inline assignment conflict refresh', () => {
  it('removes obsolete markers on all cells and restores authoritative warnings', async () => {
    const store = setup()
    const original = store.matrix?.rows[0].cells['2026-10-18']
    store.applyInlineAssignment('event-a', saved)

    expect(store.conflictsStale).toBe(true)
    expect(store.matrix?.rows[0].cells['2026-10-18']).toBe(original)
    expect(original?.leader_name).toBe('Neuer Dienstleiter')
    expect(original?.revision).toBe('"after"')
    expect(store.matrix?.rows.every((row) => row.cells['2026-10-18'].conflicts?.length === 0)).toBe(true)

    vi.mocked(fetchMatrix).mockResolvedValue(fixture([], [BLOCK]))
    await store.refreshConflicts()

    expect(store.conflictsStale).toBe(false)
    expect(store.conflictsRefreshError).toBeNull()
    expect(store.matrix?.rows[1].cells['2026-10-18'].conflicts).toEqual([BLOCK])
    expect(store.matrix?.rows[0].cells['2026-10-18'].leader_id).toBe('new')
    expect(fetchMatrix).toHaveBeenCalledWith(
      'district', '2026-10-18T00:00:00Z', '2026-10-18T23:59:59Z', undefined,
    )
  })

  it('keeps the saved assignment and signals a refresh failure without stale warnings', async () => {
    const store = setup()
    store.applyInlineAssignment('event-a', saved)
    vi.mocked(fetchMatrix).mockRejectedValue(new Error('network unavailable'))

    await store.refreshConflicts()

    expect(store.matrix?.rows[0].cells['2026-10-18'].leader_id).toBe('new')
    expect(store.conflictsStale).toBe(true)
    expect(store.conflictsRefreshError).toContain('Matrix neu laden')
    expect(store.matrix?.rows[1].cells['2026-10-18'].conflicts).toEqual([])
  })

  it('ignores an obsolete response after another inline write', async () => {
    const store = setup()
    store.applyInlineAssignment('event-a', saved)
    let finish!: (result: MatrixResponse) => void
    vi.mocked(fetchMatrix).mockImplementationOnce(
      () => new Promise<MatrixResponse>((resolve) => { finish = resolve }),
    )
    const pending = store.refreshConflicts()

    store.applyInlineAssignment('event-b', { ...saved, event_id: 'event-b' })
    finish(fixture([BLOCK], [WARN]))
    await pending

    expect(store.conflictsStale).toBe(true)
    expect(store.matrix?.rows[0].cells['2026-10-18'].conflicts).toEqual([])
    expect(store.matrix?.rows[1].cells['2026-10-18'].conflicts).toEqual([])
  })
})
