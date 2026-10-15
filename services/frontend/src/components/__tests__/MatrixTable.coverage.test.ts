// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import MatrixTable from '@/components/MatrixTable.vue'
import { useDistrictsStore } from '@/stores/districts'
import { useMatrixStore } from '@/stores/matrix'
import { useLeadersStore } from '@/stores/leaders'
import { useAuthStore } from '@/stores/auth'
import * as assignmentsApi from '@/api/serviceAssignments'
import type { MatrixResponse } from '@/api/matrix'
import { ApiError } from '@/api/errors'
import { useConfirmHost } from '@/composables/useConfirm'

vi.mock('@/api/serviceAssignments', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/serviceAssignments')>()),
  changeAssignmentInline: vi.fn(),
}))

const dates = ['2026-10-04', '2026-10-05', '2026-10-06', '2026-10-07', '2026-10-08']

const richMatrix: MatrixResponse = {
  dates,
  holidays: { '2026-10-04': ['Erntedank'] },
  rows: [
    {
      congregation_id: 'c1',
      congregation_name: 'Gemeinde A',
      group_name: 'Gruppe Nord',
      cells: {
        '2026-10-04': {
          event_id: 'gap',
          event_title: 'Offener Dienst',
          category: 'Gottesdienst',
          leader_name: null,
          leader_id: null,
          is_gap: true,
          assignment_id: null,
          assignment_status: null,
          is_assignment_editable: true,
          has_deviation: true,
          planned_time: '09:30',
          actual_start_at: '2026-10-04T10:00:00',
          invitation_count: 2,
        },
        '2026-10-05': {
          event_id: 'normal',
          event_title: 'Abendgottesdienst',
          category: 'Gottesdienst',
          leader_name: 'Max Muster',
          leader_id: 'l1',
          is_gap: false,
          assignment_id: 'a1',
          assignment_status: 'CONFIRMED',
          approval_status: 'APPROVED',
          is_assignment_editable: true,
          has_deviation: false,
          invitation_count: 1,
        },
        '2026-10-06': {
          event_id: 'hosted',
          event_title: 'Einladung',
          category: 'Jugend',
          leader_name: 'Erika Beispiel',
          leader_id: 'l2',
          is_gap: false,
          assignment_id: 'a2',
          assignment_status: 'CONFIRMED',
          is_assignment_editable: false,
          invitation_source_congregation_name: 'Gemeinde B',
        },
        '2026-10-07': {
          event_id: 'deviation',
          event_title: 'Morgengottesdienst',
          category: null,
          leader_name: null,
          leader_id: null,
          is_gap: false,
          assignment_id: 'a3',
          assignment_status: 'CONFIRMED',
          is_assignment_editable: true,
          has_deviation: true,
          planned_time: '09:30',
          actual_start_at: '10:00',
          deviation_start_diff_minutes: 30,
          deviation_end_diff_minutes: null,
        },
      },
    },
  ],
} as MatrixResponse

beforeEach(() => {
  setActivePinia(createPinia())
})

describe('MatrixTable coverage gaps', () => {
  it('renders gap, holiday, host-managed, invitation and deviation variants', async () => {
    const matrixStore = useMatrixStore()
    const districtsStore = useDistrictsStore()
    matrixStore.matrix = richMatrix
    districtsStore.congregations = [{ id: 'c1', name: 'Gemeinde A' }] as typeof districtsStore.congregations

    const wrapper = mount(MatrixTable, {
      props: { compactMode: false, matrixSortMode: 'default' },
    })
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Erntedank')
    expect(wrapper.text()).toContain('LÜCKE')
    expect(wrapper.text()).toContain('Plan: 09:30')
    expect(wrapper.text()).toContain('Einladungen: 2')
    expect(wrapper.text()).toContain('Max Muster')
    expect(wrapper.text()).toContain('Gottesdienst in Gemeinde B')
    expect(wrapper.get('[data-testid="host-congregation"]').text()).toBe('Gemeinde B')
    expect(wrapper.text()).not.toContain('Dienstleiterpflege')
    expect(wrapper.text()).not.toContain('Eingeladen nach')
    expect(wrapper.find('button[title="Der Dienstleiter wird in der Gastgeber-Gemeinde gepflegt."]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Abweichung')
    expect(wrapper.text()).toContain('–')

    const buttons = wrapper.findAll('tbody button')
    await buttons[0].trigger('click')
    await buttons[1].trigger('click')
    expect(wrapper.emitted('open-modal')).toHaveLength(2)

    await wrapper.setProps({ compactMode: true, matrixSortMode: 'grouped' })
    expect(wrapper.get('table').classes()).toContain('matrix-table--compact')
    wrapper.unmount()
  })

  it('uses the shared inline select for authorised versioned minister updates', async () => {
    const matrixStore = useMatrixStore()
    const auth = useAuthStore()
    const leaders = useLeadersStore()
    leaders.districtId = 'd1'
    matrixStore.districtId = 'd1'
    matrixStore.matrix = structuredClone(richMatrix)
    matrixStore.matrix!.rows[0].cells['2026-10-05'].revision = '"rev-1"'
    auth.memberships = [{
      scope_type: 'DISTRICT', scope_id: 'd1', role: 'PLANNER',
    }] as typeof auth.memberships
    leaders.leaders = [
      { id: 'l1', name: 'Max Muster', rank: 'Pr.', is_active: true },
      { id: 'l3', name: 'Neu', rank: 'Di.', is_active: true },
    ] as typeof leaders.leaders
    vi.mocked(assignmentsApi.changeAssignmentInline).mockResolvedValue({
      id: 'a1', event_id: 'normal', leader_id: 'l3', leader_name: null,
      status: 'ASSIGNED', event_revision: '"rev-2"',
      created_at: '', updated_at: '',
    })
    const wrapper = mount(MatrixTable, {
      props: { compactMode: false, matrixSortMode: 'default' },
    })
    expect(wrapper.get('table').attributes('data-inline-edit-scope')).toBeDefined()
    const editable = wrapper.get('[data-inline-cell-id="matrix-leader-c1-2026-10-05"]')
    await editable.trigger('click')
    await flushPromises()
    await editable.get('select').setValue('l3')
    await editable.get('select').trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(assignmentsApi.changeAssignmentInline)
      .toHaveBeenCalledWith('normal', 'l3', '"rev-1"')
    expect(matrixStore.matrix!.rows[0].cells['2026-10-05'].revision).toBe('"rev-2"')
    expect(matrixStore.matrix!.rows[0].cells['2026-10-05'].leader_name).toBe('Di. Neu')
    expect(wrapper.find('[data-inline-cell-id="matrix-leader-c1-2026-10-06"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it.each([true, undefined])('hides invitation copies even when editability is %s', (editable) => {
    const matrixStore = useMatrixStore()
    matrixStore.districtId = 'd1'
    matrixStore.matrix = structuredClone(richMatrix)
    const cell = matrixStore.matrix.rows[0].cells['2026-10-06']
    cell.revision = '"rev-1"'
    cell.is_assignment_editable = editable
    cell.assignment_event_id = 'host-event'
    useAuthStore().memberships = [{ scope_type: 'DISTRICT', scope_id: 'd1', role: 'PLANNER' }]
    const wrapper = mount(MatrixTable, {
      props: { compactMode: false, matrixSortMode: 'default' },
    })

    expect(wrapper.find('[data-inline-cell-id="matrix-leader-c1-2026-10-06"]').exists()).toBe(false)
    expect(wrapper.get('[data-testid="host-congregation"]').text()).toBe('Gemeinde B')
    wrapper.unmount()
  })

  it('does not expose inline assignment editing to viewer-only access', () => {
    const matrixStore = useMatrixStore()
    matrixStore.districtId = 'd1'
    matrixStore.matrix = structuredClone(richMatrix)
    matrixStore.matrix.rows[0].cells['2026-10-05'].revision = '"rev-1"'
    const wrapper = mount(MatrixTable, {
      props: { compactMode: true, matrixSortMode: 'default' },
    })
    expect(wrapper.find('[data-inline-cell-id="matrix-leader-c1-2026-10-05"]').exists()).toBe(false)
  })

  it('renders the no-events state when the matrix has no dates', () => {
    const matrixStore = useMatrixStore()
    matrixStore.matrix = { dates: [], rows: [], holidays: {} }

    const wrapper = mount(MatrixTable, {
      props: { compactMode: false, matrixSortMode: 'default' },
    })

    expect(wrapper.text()).toContain('Keine Ereignisse im gewählten Zeitraum.')
  })

  describe('inline assignment conflicts', () => {
    const savedResult = {
      id: 'a1', event_id: 'normal', leader_id: 'l3', leader_name: null,
      status: 'ASSIGNED' as const, event_revision: '"rev-2"', created_at: '', updated_at: '',
    }

    beforeEach(() => {
      vi.mocked(assignmentsApi.changeAssignmentInline).mockReset()
    })

    function mountEditable() {
      const matrixStore = useMatrixStore()
      const auth = useAuthStore()
      const leaders = useLeadersStore()
    leaders.districtId = 'd1'
      matrixStore.districtId = 'd1'
      matrixStore.matrix = structuredClone(richMatrix)
      matrixStore.matrix!.rows[0].cells['2026-10-05'].revision = '"rev-1"'
      auth.memberships = [{
        scope_type: 'DISTRICT', scope_id: 'd1', role: 'PLANNER',
      }] as typeof auth.memberships
      leaders.leaders = [
        { id: 'l1', name: 'Max Muster', rank: 'Pr.', is_active: true },
        { id: 'l3', name: 'Neu', rank: 'Di.', is_active: true },
      ] as typeof leaders.leaders

      const wrapper = mount(MatrixTable, {
        props: { compactMode: false, matrixSortMode: 'default' },
      })
      return { wrapper, matrixStore }
    }

    async function submitLeader(wrapper: ReturnType<typeof mountEditable>['wrapper']) {
      const editable = wrapper.get('[data-inline-cell-id="matrix-leader-c1-2026-10-05"]')
      await editable.trigger('click')
      await flushPromises()
      await editable.get('select').setValue('l3')
      await editable.get('select').trigger('keydown', { key: 'Enter' })
      await flushPromises()
    }

    function conflictError(severity: 'WARN' | 'BLOCK') {
      return new ApiError(409, 'Conflict', {
        detail: { conflicts: [{ rule_id: 'R1', severity, message: `Konflikt ${severity}`, details: {} }] },
      })
    }

    it('acknowledges warning-only conflicts and resends with confirm_warnings', async () => {
      vi.mocked(assignmentsApi.changeAssignmentInline)
        .mockRejectedValueOnce(conflictError('WARN'))
        .mockResolvedValueOnce(savedResult)
      const { wrapper, matrixStore } = mountEditable()
      await submitLeader(wrapper)

      const dialog = useConfirmHost()
      expect(dialog.isRevealed.value).toBe(true)
      expect(dialog.options.value?.message).toContain('Konflikt WARN')
      dialog.confirm()
      await flushPromises()

      expect(assignmentsApi.changeAssignmentInline).toHaveBeenLastCalledWith('normal', 'l3', '"rev-1"', true)
      expect(matrixStore.matrix!.rows[0].cells['2026-10-05'].revision).toBe('"rev-2"')
      wrapper.unmount()
    })

    it('keeps the draft and sends nothing more when the warning is cancelled', async () => {
      vi.mocked(assignmentsApi.changeAssignmentInline).mockRejectedValueOnce(conflictError('WARN'))
      const { wrapper } = mountEditable()
      await submitLeader(wrapper)

      useConfirmHost().cancel()
      await flushPromises()

      expect(assignmentsApi.changeAssignmentInline).toHaveBeenCalledOnce()
      expect(wrapper.get('[role="alert"]').text()).toContain('abgebrochen')
      expect(wrapper.find('select').exists()).toBe(true)
      wrapper.unmount()
    })

    it('shows blocking conflicts without offering acknowledgement', async () => {
      vi.mocked(assignmentsApi.changeAssignmentInline).mockRejectedValueOnce(conflictError('BLOCK'))
      const { wrapper } = mountEditable()
      await submitLeader(wrapper)

      expect(useConfirmHost().isRevealed.value).toBe(false)
      expect(wrapper.get('[role="alert"]').text()).toContain('Konflikt BLOCK')
      expect(assignmentsApi.changeAssignmentInline).toHaveBeenCalledOnce()
      wrapper.unmount()
    })

    it.each([
      { district: 'd2', loading: false },
      { district: 'd1', loading: true },
    ])('hides choices that are mismatched or still loading: %j', async ({ district, loading }) => {
      const { wrapper } = mountEditable()
      const leaders = useLeadersStore()
      leaders.districtId = district
      leaders.loading = loading
      await wrapper.vm.$nextTick()
      expect(wrapper.find('[data-inline-cell-id="matrix-leader-c1-2026-10-05"]').exists()).toBe(false)
      wrapper.unmount()
    })

    it('sends a single request on repeated submit while saving', async () => {
      let finish: (value: typeof savedResult) => void = () => {}
      vi.mocked(assignmentsApi.changeAssignmentInline).mockImplementation(
        () => new Promise((resolve) => { finish = resolve }),
      )
      const { wrapper } = mountEditable()
      const editable = wrapper.get('[data-inline-cell-id="matrix-leader-c1-2026-10-05"]')
      await editable.trigger('click')
      await flushPromises()
      await editable.get('select').setValue('l3')
      await editable.get('select').trigger('keydown', { key: 'Enter' })
      await editable.get('select').trigger('keydown', { key: 'Enter' })
      expect(assignmentsApi.changeAssignmentInline).toHaveBeenCalledOnce()

      finish(savedResult)
      await flushPromises()
      wrapper.unmount()
    })
  })
})
