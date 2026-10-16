// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { LeaderResponse } from '../api/leaders'
import type { LeaderUnavailabilityResponse } from '../api/leaderUnavailabilities'
import LeaderUnavailabilityList from './LeaderUnavailabilityList.vue'

const leaders = [
  { id: 'l1', name: 'Anna', rank: 'Pr.' },
  { id: 'l2', name: 'Bernd', rank: null },
] as LeaderResponse[]

const items = [
  { id: 'u1', leader_id: 'l1', start_date: '2026-11-01', end_date: '2026-11-03', reason: 'VACATION', note: null },
  { id: 'u2', leader_id: 'l2', start_date: '2026-11-10', end_date: '2026-11-10', reason: 'ILLNESS', note: 'krank' },
] as unknown as LeaderUnavailabilityResponse[]

describe('LeaderUnavailabilityList (read-only table)', () => {
  it('renders compact table cells without any inline editor', () => {
    const wrapper = mount(LeaderUnavailabilityList, { props: { items, leaders, canDelete: true } })
    const table = wrapper.get('[data-testid="unavailability-table"]')
    expect(table.get('thead').classes()).toContain('table-thead')
    expect(table.classes()).toContain('table-min-w')
    expect(table.findAll('tbody tr')).toHaveLength(2)
    expect(table.find('[data-inline-editable]').exists()).toBe(false)
    expect(table.find('input, select, textarea').exists()).toBe(false)
  })

  it('does not become editable on click, Enter or F2', async () => {
    const wrapper = mount(LeaderUnavailabilityList, { props: { items, leaders, canDelete: true } })
    const cell = wrapper.get('tbody td')
    for (const trigger of [() => cell.trigger('click'), () => cell.trigger('keydown', { key: 'Enter' }), () => cell.trigger('keydown', { key: 'F2' })]) {
      await trigger()
    }
    expect(wrapper.find('tbody input, tbody select').exists()).toBe(false)
  })

  it('offers deletion only to authorised users and only as an explicit action', async () => {
    const readOnly = mount(LeaderUnavailabilityList, { props: { items, leaders, canDelete: false } })
    expect(readOnly.find('[data-testid="unavailability-delete-u1"]').exists()).toBe(false)

    const admin = mount(LeaderUnavailabilityList, { props: { items, leaders, canDelete: true } })
    await admin.get('[data-testid="unavailability-delete-u1"]').trigger('click')
    expect(admin.emitted('delete')?.[0][0]).toMatchObject({ id: 'u1' })
  })

  it('filters by leader without changing any data', async () => {
    const wrapper = mount(LeaderUnavailabilityList, { props: { items, leaders } })
    await wrapper.get('[data-testid="unavailability-filter-select"]').setValue('l2')
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
    expect(wrapper.emitted('update:filter-leader-id')?.[0]).toEqual(['l2'])
  })
})
