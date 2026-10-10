// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import type { MatrixCell } from '../api/matrix'
import { useDistrictsStore } from '../stores/districts'
import { useLeadersStore } from '../stores/leaders'
import { useMatrixStore } from '../stores/matrix'
import MatrixView from './MatrixView.vue'
import { useAuthStore } from '../stores/auth'

const assignmentOpen = vi.fn()

const MatrixFiltersStub = defineComponent({
  props: {
    compactMode: Boolean,
    matrixSortMode: String,
  },
  emits: ['update:compact-mode', 'update:matrix-sort-mode', 'release'],
  setup(_, { emit }) {
    return () => h('div', [
      h('button', { 'data-test': 'compact', onClick: () => emit('update:compact-mode', true) }, 'compact'),
      h('button', { 'data-test': 'grouped', onClick: () => emit('update:matrix-sort-mode', 'grouped') }, 'grouped'),
      h('button', { 'data-test': 'release', onClick: () => emit('release') }, 'release'),
    ])
  },
})

const MatrixTableStub = defineComponent({
  emits: ['open-modal'],
  setup(_, { emit }) {
    return () => h('button', {
      'data-test': 'open-assignment',
      onClick: () => emit('open-modal', {
        cell: { event_id: 'event-1', assignment_event_id: 'event-1', is_gap: true } as MatrixCell,
        date: '2026-10-05',
        congregationName: 'Gemeinde A',
        congregationId: 'cong-1',
      }),
    }, 'open')
  },
})

const AssignmentModalStub = defineComponent({
  setup(_, { expose }) {
    expose({ open: assignmentOpen })
    return () => h('div')
  },
})

const MonthlyReleaseDialogStub = defineComponent({
  props: { open: Boolean, districtId: String },
  emits: ['close', 'released'],
  setup(props, { emit }) {
    return () => h('div', { 'data-test': 'release-dialog', 'data-open': String(props.open) }, [
      h('button', { 'data-test': 'released', onClick: () => emit('released', 2) }, 'released'),
      h('button', { 'data-test': 'close-release', onClick: () => emit('close') }, 'close'),
    ])
  },
})

function setup(options: { districtId?: string; range?: boolean } = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  useAuthStore().user = { sub: 'test-user' }
  const districts = useDistrictsStore()
  const leaders = useLeadersStore()
  const matrix = useMatrixStore()
  districts.districts = [{ id: 'd1', name: 'District 1' }] as typeof districts.districts
  districts.selectedDistrictId = options.districtId ?? 'd1'
  matrix.districtId = options.districtId ?? 'd1'
  if (options.range !== false) {
    matrix.fromDt = '2026-10-01'
    matrix.toDt = '2026-10-31'
  }

  vi.spyOn(districts, 'fetchDistricts').mockResolvedValue(undefined)
  vi.spyOn(districts, 'fetchGroups').mockResolvedValue(undefined)
  vi.spyOn(districts, 'fetchCongregations').mockResolvedValue(undefined)
  vi.spyOn(leaders, 'fetchLeaders').mockResolvedValue(undefined)
  vi.spyOn(matrix, 'fetch').mockResolvedValue(undefined)

  const wrapper = mount(MatrixView, {
    global: {
      plugins: [pinia],
      stubs: {
        MatrixFilters: MatrixFiltersStub,
        MatrixTable: MatrixTableStub,
        AssignmentModal: AssignmentModalStub,
        MonthlyReleaseDialog: MonthlyReleaseDialogStub,
        MatrixSkeleton: { template: '<div data-test="skeleton">loading</div>' },
        ContextualHelp: true,
      },
    },
  })
  return { wrapper, districts, leaders, matrix }
}

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
  sessionStorage.clear()
})

describe('MatrixView', () => {
  it('restores a group that is still accessible and repairs an empty date range', async () => {
    sessionStorage.setItem('planner.view-settings.v1:' + JSON.stringify(['test-user', 'matrix', 'd1']),
      JSON.stringify({ group: 'g1', from: '', to: '', sort: 'default' }))
    const ctx = setup()
    ctx.districts.groups = [{
      id: 'g1', name: 'Available', district_id: 'd1',
      created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z',
    }]
    await flushPromises()
    expect(ctx.matrix.groupId).toBe('g1')
    expect(ctx.matrix.fromDt).toMatch(/^\d{4}-\d{2}-01$/)
    expect(ctx.matrix.toDt).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    ctx.wrapper.unmount()
  })

  it('clears active filters and sorting on logout', async () => {
    const ctx = setup()
    await flushPromises()
    ctx.matrix.congregationQuery = 'Private'
    await ctx.wrapper.get('[data-test="grouped"]').trigger('click')
    useAuthStore().clearAuth()
    await flushPromises()
    expect(ctx.matrix.congregationQuery).toBe('')
    expect(ctx.wrapper.findComponent(MatrixFiltersStub).props('matrixSortMode')).toBe('default')
    expect(ctx.matrix.districtId).toBe('')
    expect(sessionStorage.length).toBe(0)
    ctx.wrapper.unmount()
  })

  it('restores query, dates and sorting after remounting with a fresh store', async () => {
    const first = setup()
    await flushPromises()
    first.matrix.congregationQuery = 'Gemeinde A'
    first.matrix.fromDt = '2026-11-01'
    first.matrix.toDt = '2026-11-30'
    await first.wrapper.get('[data-test="grouped"]').trigger('click')
    first.wrapper.unmount()

    const second = setup()
    await flushPromises()
    expect(second.matrix.congregationQuery).toBe('Gemeinde A')
    expect(second.matrix.fromDt).toBe('2026-11-01')
    expect(second.matrix.toDt).toBe('2026-11-30')
    expect(second.wrapper.findComponent(MatrixFiltersStub).props('matrixSortMode')).toBe('grouped')
    expect(second.matrix.fetch).toHaveBeenCalled()
    second.wrapper.unmount()
  })

  it('keeps district filters independent and removes unavailable groups', async () => {
    const ctx = setup()
    await flushPromises()
    ctx.matrix.congregationQuery = 'District one'
    ctx.matrix.groupId = 'deleted-group'
    ctx.districts.selectedDistrictId = 'd2'
    await flushPromises()
    expect(ctx.matrix.congregationQuery).toBe('')
    ctx.matrix.congregationQuery = 'District two'
    ctx.districts.selectedDistrictId = 'd1'
    await flushPromises()
    expect(ctx.matrix.congregationQuery).toBe('District one')
    expect(ctx.matrix.groupId).toBe('')
    ctx.wrapper.unmount()
  })

  it('hydrates persisted view preferences and loads district dependencies on mount', async () => {
    localStorage.setItem('matrix.compactMode', '1')
    sessionStorage.setItem('planner.view-settings.v1:' + JSON.stringify(['test-user', 'matrix', 'd1']), JSON.stringify({ sort: 'grouped' }))
    const ctx = setup()
    await flushPromises()

    expect(ctx.districts.fetchGroups).toHaveBeenCalledWith('d1')
    expect(ctx.districts.fetchCongregations).toHaveBeenCalledWith('d1')
    expect(ctx.leaders.fetchLeaders).toHaveBeenCalledWith('d1')
    expect(ctx.matrix.fetch).toHaveBeenCalled()
    expect(ctx.wrapper.findComponent(MatrixFiltersStub).props('compactMode')).toBe(true)
    expect(ctx.wrapper.findComponent(MatrixFiltersStub).props('matrixSortMode')).toBe('grouped')
  })

  it('creates a default month range when none is stored', async () => {
    const ctx = setup({ range: false })
    await flushPromises()

    expect(ctx.matrix.fromDt).toMatch(/^\d{4}-\d{2}-01$/)
    expect(ctx.matrix.toDt).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })

  it('persists compact and sort mode changes', async () => {
    const ctx = setup()
    await flushPromises()

    await ctx.wrapper.get('[data-test="compact"]').trigger('click')
    await ctx.wrapper.get('[data-test="grouped"]').trigger('click')

    expect(localStorage.getItem('matrix.compactMode')).toBe('1')
    expect(JSON.parse(sessionStorage.getItem('planner.view-settings.v1:' + JSON.stringify(['test-user', 'matrix', 'd1']))!).sort).toBe('grouped')
    expect(localStorage.getItem('matrix.sortMode')).toBeNull()
  })

  it('reloads district data when the global selection changes', async () => {
    const ctx = setup()
    await flushPromises()
    vi.clearAllMocks()

    ctx.districts.selectedDistrictId = 'd2'
    await flushPromises()

    expect(ctx.matrix.districtId).toBe('d2')
    expect(ctx.matrix.groupId).toBe('')
    expect(ctx.districts.fetchGroups).toHaveBeenCalledWith('d2')
    expect(ctx.districts.fetchCongregations).toHaveBeenCalledWith('d2')
    expect(ctx.leaders.fetchLeaders).toHaveBeenCalledWith('d2')
    expect(ctx.matrix.fetch).toHaveBeenCalled()
  })

  it('does not refetch when the selected district already matches the matrix', async () => {
    const ctx = setup()
    await flushPromises()
    vi.clearAllMocks()

    ctx.districts.selectedDistrictId = 'd1'
    await flushPromises()

    expect(ctx.districts.fetchGroups).not.toHaveBeenCalled()
  })

  it('bridges the table open event to the assignment modal public API', async () => {
    const ctx = setup()
    await flushPromises()

    await ctx.wrapper.get('[data-test="open-assignment"]').trigger('click')

    expect(assignmentOpen).toHaveBeenCalledWith(
      expect.objectContaining({ event_id: 'event-1' }),
      '2026-10-05',
      'Gemeinde A',
      'cong-1',
    )
  })

  it('opens the monthly release dialog and refreshes after a release', async () => {
    const ctx = setup()
    await flushPromises()
    vi.mocked(ctx.matrix.fetch).mockClear()

    await ctx.wrapper.get('[data-test="release"]').trigger('click')
    expect(ctx.wrapper.get('[data-test="release-dialog"]').attributes('data-open')).toBe('true')

    await ctx.wrapper.get('[data-test="released"]').trigger('click')
    await ctx.wrapper.vm.$nextTick()
    expect(ctx.wrapper.get('[data-test="release-dialog"]').attributes('data-open')).toBe('false')
    expect(ctx.matrix.fetch).toHaveBeenCalled()
  })

  it('renders loading and error states from the matrix store', async () => {
    const ctx = setup()
    await flushPromises()

    ctx.matrix.loading = true
    await ctx.wrapper.vm.$nextTick()
    expect(ctx.wrapper.find('[data-test="skeleton"]').exists()).toBe(true)

    ctx.matrix.loading = false
    ctx.matrix.error = 'Matrix konnte nicht geladen werden'
    await ctx.wrapper.vm.$nextTick()
    expect(ctx.wrapper.text()).toContain('Matrix konnte nicht geladen werden')
  })
})
