import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useMatrixStore } from './matrix'
import * as matrixApi from '../api/matrix'
import * as assignmentsApi from '../api/serviceAssignments'

vi.mock('../api/matrix')
vi.mock('../api/serviceAssignments')

describe('useMatrixStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(matrixApi.fetchMatrix).mockResolvedValue({ dates: [], rows: [], holidays: {} })
    vi.mocked(assignmentsApi.createAssignment).mockResolvedValue({
      id: 'a1',
      event_id: 'e1',
      leader_id: null,
      leader_name: 'Leader',
      status: 'ASSIGNED',
      created_at: '2026-04-07T00:00:00Z',
      updated_at: '2026-04-07T00:00:00Z',
    })
    vi.mocked(assignmentsApi.updateAssignment).mockResolvedValue({
      id: 'a1',
      event_id: 'e1',
      leader_id: null,
      leader_name: null,
      status: 'OPEN',
      created_at: '2026-04-07T00:00:00Z',
      updated_at: '2026-04-07T00:00:00Z',
    })
  })

  it('assign triggers matrix refresh', async () => {
    const store = useMatrixStore()
    store.districtId = 'd1'
    store.fromDt = '2026-04-01'
    store.toDt = '2026-04-30'

    await store.assign('e1', null, { leaderName: 'Max' })
    expect(assignmentsApi.createAssignment).toHaveBeenCalledWith(
      'e1',
      { leaderName: 'Max' },
      'ASSIGNED',
    )
    expect(matrixApi.fetchMatrix).toHaveBeenCalled()
  })

  it('assign updates existing assignment when assignment id exists', async () => {
    const store = useMatrixStore()
    store.districtId = 'd1'
    store.fromDt = '2026-04-01'
    store.toDt = '2026-04-30'

    await store.assign('e1', 'a1', { leaderId: 'l1' })
    expect(assignmentsApi.updateAssignment).toHaveBeenCalledWith(
      'e1',
      'a1',
      { leaderId: 'l1' },
      'ASSIGNED',
    )
  })

  it('clearAssignment sets assignment back to OPEN', async () => {
    const store = useMatrixStore()
    store.districtId = 'd1'
    store.fromDt = '2026-04-01'
    store.toDt = '2026-04-30'

    await store.clearAssignment('e1', 'a1')
    expect(assignmentsApi.updateAssignment).toHaveBeenCalledWith(
      'e1',
      'a1',
      { leaderId: null, leaderName: null },
      'OPEN',
    )
    expect(matrixApi.fetchMatrix).toHaveBeenCalled()
  })

  it('decides overwrite request through dedicated store', async () => {
    const store = useMatrixStore()
    store.districtId = 'd1'
    store.fromDt = '2026-04-01'
    store.toDt = '2026-04-30'
    await store.assign('e1', null, { leaderName: 'Max' })
    expect(assignmentsApi.createAssignment).toHaveBeenCalledWith(
      'e1',
      { leaderName: 'Max' },
      'ASSIGNED',
    )
  })
})
