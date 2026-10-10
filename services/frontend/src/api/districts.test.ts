// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./client')

import * as client from './client'
import {
  createCongregation,
  createDistrict,
  createGroup,
  deleteGroup,
  generateMatrixDraftServices,
  importFeiertage,
  listCongregations,
  listDeStates,
  listDistricts,
  listGroups,
  updateCongregation,
  updateDistrict,
  updateGroup,
} from './districts'

const apiFetch = vi.mocked(client.apiFetch)

describe('district API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiFetch.mockResolvedValue({})
  })

  it('lists and mutates districts', async () => {
    await listDistricts()
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/districts')

    await createDistrict('Tuttlingen')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/districts', {
      method: 'POST',
      body: JSON.stringify({ name: 'Tuttlingen', state_code: null }),
    })

    await createDistrict('Konstanz', 'BW')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/districts', {
      method: 'POST',
      body: JSON.stringify({ name: 'Konstanz', state_code: 'BW' }),
    })

    await updateDistrict('district-1', { name: 'Neu', state_code: null })
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/districts/district-1', {
      method: 'PATCH',
      body: JSON.stringify({ name: 'Neu', state_code: null }),
    })
  })

  it('lists congregations with and without a group filter', async () => {
    await listCongregations('district-1')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/districts/district-1/congregations')

    await listCongregations('district-1', 'group-1')
    expect(apiFetch).toHaveBeenLastCalledWith(
      '/api/v1/districts/district-1/congregations?group_id=group-1',
    )
  })

  it('creates and updates congregations with optional values normalized', async () => {
    await createCongregation('district-1', 'Stockach')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/districts/district-1/congregations', {
      method: 'POST',
      body: JSON.stringify({ name: 'Stockach', service_times: null, group_id: null }),
    })

    const serviceTimes = [{ weekday: 6, time: '09:30' }]
    await createCongregation('district-1', 'Tuttlingen', serviceTimes, 'group-1')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/districts/district-1/congregations', {
      method: 'POST',
      body: JSON.stringify({ name: 'Tuttlingen', service_times: serviceTimes, group_id: 'group-1' }),
    })

    await updateCongregation('district-1', 'congregation-1', { name: 'Neu', group_id: null })
    expect(apiFetch).toHaveBeenLastCalledWith(
      '/api/v1/districts/district-1/congregations/congregation-1',
      { method: 'PATCH', body: JSON.stringify({ name: 'Neu', group_id: null }) },
    )
  })

  it('covers congregation group CRUD', async () => {
    await listGroups('district-1')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/districts/district-1/groups')

    await createGroup('district-1', 'Nord')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/districts/district-1/groups', {
      method: 'POST',
      body: JSON.stringify({ name: 'Nord' }),
    })

    await updateGroup('district-1', 'group-1', 'Süd')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/districts/district-1/groups/group-1', {
      method: 'PATCH',
      body: JSON.stringify({ name: 'Süd' }),
    })

    await deleteGroup('district-1', 'group-1')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/districts/district-1/groups/group-1', {
      method: 'DELETE',
    })
  })

  it('covers holiday import and matrix draft generation', async () => {
    await listDeStates('district-1')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/districts/district-1/feiertage/states')

    await importFeiertage('district-1', 2027, 'BW')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/districts/district-1/feiertage', {
      method: 'POST',
      body: JSON.stringify({ year: 2027, state_code: 'BW' }),
    })

    await generateMatrixDraftServices('district-1', '2027-01-01', '2027-01-31')
    const [url, options] = apiFetch.mock.calls.at(-1)!
    expect(url).toContain('/api/v1/districts/district-1/matrix/generate-drafts?')
    expect(url).toContain('from_dt=2027-01-01')
    expect(url).toContain('to_dt=2027-01-31')
    expect(options).toEqual({ method: 'POST' })
  })
})
