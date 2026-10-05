import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, flushPromises, h } from 'vue'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import type { MatrixCell } from '../api/matrix'
import { useDistrictsStore } from '../stores/districts'
import { useLeadersStore } from '../stores/leaders'
import { useMatrixStore } from '../stores/matrix'
import MatrixView from './MatrixView.vue'

const assignmentOpen = vi.fn()

const MatrixFiltersStub = defineComponent({
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
})

describe('MatrixView', () => {
  it('hydrates persisted view preferences and loads district dependencies on mount', async () => {
    localStorage.setItem('matrix.compactMode', '1')
    localStorage.setItem('matrix.sortMode', 'grouped')
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
    expect(localStorage.getItem('matrix.sortMode')).toBe('grouped')
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
