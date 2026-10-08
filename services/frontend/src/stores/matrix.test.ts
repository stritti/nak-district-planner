import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useMatrixStore } from './matrix'
import * as matrixApi from '../api/matrix'
import * as assignmentsApi from '../api/serviceAssignments'
import * as districtsApi from '../api/districts'
import { ApiError, ConflictError } from '../api/errors'

vi.mock('../api/matrix')
vi.mock('../api/serviceAssignments')
vi.mock('../api/districts')

function configureRange(store: ReturnType<typeof useMatrixStore>) {
  store.districtId = 'd1'
  store.fromDt = '2026-04-01'
  store.toDt = '2026-04-30'
}

describe('useMatrixStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(matrixApi.fetchMatrix).mockResolvedValue({ dates: [], rows: [], holidays: {} })
    vi.mocked(assignmentsApi.createAssignment).mockResolvedValue({
      id: 'a1', event_id: 'e1', leader_id: null, leader_name: 'Leader', status: 'ASSIGNED',
      created_at: '2026-04-07T00:00:00Z', updated_at: '2026-04-07T00:00:00Z',
    })
    vi.mocked(assignmentsApi.updateAssignment).mockResolvedValue({
      id: 'a1', event_id: 'e1', leader_id: null, leader_name: null, status: 'OPEN',
      created_at: '2026-04-07T00:00:00Z', updated_at: '2026-04-07T00:00:00Z',
    })
    vi.mocked(assignmentsApi.deleteAssignment).mockResolvedValue()
    vi.mocked(districtsApi.generateMatrixDraftServices).mockResolvedValue({ created_count: 2 })
  })

  it('does not fetch until district and date range are complete', async () => {
    const store = useMatrixStore()
    await store.fetch()
    expect(matrixApi.fetchMatrix).not.toHaveBeenCalled()
  })

  it('fetches matrix with optional group and resets loading/error', async () => {
    const store = useMatrixStore()
    configureRange(store)
    store.groupId = 'group-1'
    store.error = 'old error'

    await store.fetch()

    expect(matrixApi.fetchMatrix).toHaveBeenCalledWith(
      'd1', '2026-04-01', '2026-04-30', 'group-1',
    )
    expect(store.matrix).toEqual({ dates: [], rows: [], holidays: {} })
    expect(store.error).toBeNull()
    expect(store.loading).toBe(false)
  })

  it.each([
    [new Error('Matrix kaputt'), 'Matrix kaputt'],
    ['not-an-error', 'Unbekannter Fehler'],
  ])('records fetch failures without leaving loading active', async (failure, expected) => {
    vi.mocked(matrixApi.fetchMatrix).mockRejectedValueOnce(failure)
    const store = useMatrixStore()
    configureRange(store)

    await store.fetch()

    expect(store.error).toBe(expected)
    expect(store.loading).toBe(false)
  })

  it('creates a new assignment with default and explicit status then refreshes', async () => {
    const store = useMatrixStore()
    configureRange(store)

    await store.assign('e1', null, { leaderName: 'Max' })
    expect(assignmentsApi.createAssignment).toHaveBeenLastCalledWith(
      'e1', { leaderName: 'Max' }, 'ASSIGNED',
    )

    await store.assign('e1', null, { leaderId: 'l1' }, 'CONFIRMED')
    expect(assignmentsApi.createAssignment).toHaveBeenLastCalledWith(
      'e1', { leaderId: 'l1' }, 'CONFIRMED',
    )
    expect(matrixApi.fetchMatrix).toHaveBeenCalledTimes(2)
  })

  it('updates existing assignments with and without explicit status', async () => {
    const store = useMatrixStore()
    configureRange(store)

    await store.assign('e1', 'a1', { leaderId: 'l1' })
    expect(assignmentsApi.updateAssignment).toHaveBeenLastCalledWith(
      'e1', 'a1', { leaderId: 'l1' },
    )

    await store.assign('e1', 'a1', { leaderName: 'Max' }, 'CONFIRMED')
    expect(assignmentsApi.updateAssignment).toHaveBeenLastCalledWith(
      'e1', 'a1', { leaderName: 'Max' }, 'CONFIRMED',
    )
  })

  it('converts structured 409 responses into ConflictError and preserves other errors', async () => {
    const conflicts = [{ rule_id: 'double', severity: 'BLOCK' as const, message: 'Doppelt', details: {} }]
    vi.mocked(assignmentsApi.createAssignment).mockRejectedValueOnce(
      new ApiError(409, 'Conflict', { detail: { conflicts } }),
    )
    const store = useMatrixStore()
    configureRange(store)

    const conflict = await store.assign('e1', null, { leaderName: 'Max' }).catch((error) => error)
    expect(conflict).toBeInstanceOf(ConflictError)
    expect((conflict as ConflictError).conflicts).toEqual(conflicts)
    expect(matrixApi.fetchMatrix).not.toHaveBeenCalled()

    const rawError = new Error('network')
    vi.mocked(assignmentsApi.createAssignment).mockRejectedValueOnce(rawError)
    await expect(store.assign('e1', null, { leaderName: 'Max' })).rejects.toBe(rawError)
  })

  it('clears existing assignments and only refreshes when no assignment exists', async () => {
    const store = useMatrixStore()
    configureRange(store)

    await store.clearAssignment('e1', 'a1')
    expect(assignmentsApi.deleteAssignment).toHaveBeenCalledWith('e1', 'a1')
    expect(matrixApi.fetchMatrix).toHaveBeenCalledTimes(1)

    vi.clearAllMocks()
    vi.mocked(matrixApi.fetchMatrix).mockResolvedValue({ dates: [], rows: [], holidays: {} })
    await store.clearAssignment('e1', null)
    expect(assignmentsApi.deleteAssignment).not.toHaveBeenCalled()
    expect(matrixApi.fetchMatrix).toHaveBeenCalledTimes(1)
  })

  it('requires a complete range before generating drafts', async () => {
    const store = useMatrixStore()
    await expect(store.generateDraftsForCurrentRange()).rejects.toThrow(
      'Bezirk und Zeitraum sind erforderlich',
    )
    expect(districtsApi.generateMatrixDraftServices).not.toHaveBeenCalled()
  })

  it('generates drafts for the current range and refreshes the matrix', async () => {
    const store = useMatrixStore()
    configureRange(store)

    await expect(store.generateDraftsForCurrentRange()).resolves.toEqual({ created_count: 2 })
    expect(districtsApi.generateMatrixDraftServices).toHaveBeenCalledWith(
      'd1', '2026-04-01', '2026-04-30',
    )
    expect(matrixApi.fetchMatrix).toHaveBeenCalledOnce()
  })
})
