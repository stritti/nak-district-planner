// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import LeaderUnavailabilityList from '@/components/LeaderUnavailabilityList.vue'
import type { LeaderResponse } from '@/api/leaders'
import type { LeaderUnavailabilityResponse } from '@/api/leaderUnavailabilities'

const leaders: LeaderResponse[] = [
  {
    id: 'leader-1',
    name: 'Pastor Schmidt',
    district_id: 'district-1',
    rank: 'Pr.',
    congregation_id: null,
    special_role: null,
    user_sub: null,
    email: null,
    phone: null,
    notes: null,
    is_active: true,
    created_at: '2026-01-01T00:00:00.000Z',
    updated_at: '2026-01-01T00:00:00.000Z',
  },
  {
    id: 'leader-2',
    name: 'Diakon Weber',
    district_id: 'district-1',
    rank: 'Di.',
    congregation_id: null,
    special_role: null,
    user_sub: null,
    email: null,
    phone: null,
    notes: null,
    is_active: true,
    created_at: '2026-01-01T00:00:00.000Z',
    updated_at: '2026-01-01T00:00:00.000Z',
  },
]

const items: LeaderUnavailabilityResponse[] = [
  {
    id: 'unavail-1',
    leader_id: 'leader-1',
    start_at: '2026-05-01T00:00:00.000Z',
    end_at: '2026-05-03T23:59:00.000Z',
    reason: 'URLAUB',
    note: 'Familienurlaub',
    created_at: '2026-04-01T00:00:00.000Z',
    updated_at: '2026-04-01T00:00:00.000Z',
  },
  {
    id: 'unavail-2',
    leader_id: 'leader-2',
    start_at: '2026-06-01T00:00:00.000Z',
    end_at: '2026-06-02T23:59:00.000Z',
    reason: 'SPERRZEIT',
    note: null,
    created_at: '2026-04-01T00:00:00.000Z',
    updated_at: '2026-04-01T00:00:00.000Z',
  },
]

function mountList(props: Partial<InstanceType<typeof LeaderUnavailabilityList>['$props']> = {}) {
  return mount(LeaderUnavailabilityList, {
    props: { items, leaders, ...props },
  })
}

describe('LeaderUnavailabilityList', () => {
  it('renders all items when no filter is selected', () => {
    const wrapper = mountList()
    expect(wrapper.findAll('tbody tr')).toHaveLength(2)
    expect(wrapper.text()).toContain('Pastor Schmidt')
    expect(wrapper.text()).toContain('Diakon Weber')
  })

  it('shows the empty state when there are no items', () => {
    const wrapper = mountList({ items: [] })
    expect(wrapper.text()).toContain('Keine Abwesenheiten erfasst.')
    expect(wrapper.find('[data-testid="unavailability-table"]').exists()).toBe(false)
  })

  it('shows the loading state', () => {
    const wrapper = mountList({ loading: true })
    expect(wrapper.text()).toContain('Lade Abwesenheiten…')
  })

  it('filters items by the selected leader', async () => {
    const wrapper = mountList({ presetLeaderId: 'leader-2' })
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
    const tbodyText = wrapper.find('tbody').text()
    expect(tbodyText).toContain('Diakon Weber')
    expect(tbodyText).not.toContain('Pastor Schmidt')
  })

  it('filters items when the leader filter is changed', async () => {
    const wrapper = mountList()
    await wrapper.find('[data-testid="unavailability-filter-select"]').setValue('leader-1')
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
    expect(wrapper.find('tbody').text()).toContain('Pastor Schmidt')
  })

  it('emits delete with the item when the delete button is clicked', async () => {
    const wrapper = mountList({ canDelete: true })
    await wrapper.find('[data-testid="unavailability-delete-unavail-1"]').trigger('click')
    const events = wrapper.emitted('delete')
    expect(events).toHaveLength(1)
    expect((events![0]![0] as LeaderUnavailabilityResponse).id).toBe('unavail-1')
  })

  it('hides delete controls in read-only mode', () => {
    const wrapper = mountList({ canDelete: false })
    expect(wrapper.find('[data-testid="unavailability-delete-unavail-1"]').exists()).toBe(false)
  })

  it('renders German reason labels', () => {
    const wrapper = mountList()
    expect(wrapper.text()).toContain('Urlaub')
    expect(wrapper.text()).toContain('Sperrzeit')
  })
})
