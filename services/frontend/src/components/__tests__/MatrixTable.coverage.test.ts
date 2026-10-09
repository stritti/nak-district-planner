import { beforeEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import MatrixTable from '@/components/MatrixTable.vue'
import { useDistrictsStore } from '@/stores/districts'
import { useMatrixStore } from '@/stores/matrix'
import type { MatrixResponse } from '@/api/matrix'

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
  it('shows where an invited service goes instead of a gap', async () => {
    const matrixStore = useMatrixStore()
    matrixStore.matrix = {
      dates: ['2026-10-04'],
      holidays: {},
      rows: [
        {
          congregation_id: 'c1',
          congregation_name: 'Gemeinde A',
          group_name: null,
          cells: {
            '2026-10-04': {
              event_id: 'e1',
              event_title: 'Gottesdienst',
              category: 'Gottesdienst',
              is_gap: false,
              assignment_id: null,
              assignment_status: null,
              leader_id: null,
              leader_name: null,
              is_assignment_editable: true,
              invitation_count: 2,
              invitation_targets: ['Nachbarort', 'Nachbarbezirk'],
            },
          },
        },
      ],
    } as MatrixResponse

    const wrapper = mount(MatrixTable, { props: { compactMode: false, matrixSortMode: 'default' } })
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).not.toContain('LÜCKE')
    expect(wrapper.get('[data-testid="invited-to"]').text()).toBe('Eingeladen nach Nachbarort, Nachbarbezirk')
  })

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
    expect(wrapper.text()).toContain('Gemeinde B')
    expect(wrapper.text()).toContain('Dienstleiterpflege in Host-Gemeinde')
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

  it('renders the no-events state when the matrix has no dates', () => {
    const matrixStore = useMatrixStore()
    matrixStore.matrix = { dates: [], rows: [], holidays: {} }

    const wrapper = mount(MatrixTable, {
      props: { compactMode: false, matrixSortMode: 'default' },
    })

    expect(wrapper.text()).toContain('Keine Ereignisse im gewählten Zeitraum.')
  })
})
