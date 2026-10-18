// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import MatrixTable from '@/components/MatrixTable.vue'
import { useMatrixStore } from '@/stores/matrix'
import type { MatrixResponse, MatrixRow } from '@/api/matrix'

function row(name: string, groupName: string | null = null): MatrixRow {
  return { congregation_id: `${name}-id`, congregation_name: name, group_name: groupName, cells: {} }
}

const matrix: MatrixResponse = {
  dates: ['2026-10-04'],
  rows: [row('Zürich-Nord', 'Ring A'), row('Basel'), row('Bern', 'Ring B')],
  holidays: {},
}

function mountTable() {
  const store = useMatrixStore()
  store.matrix = matrix
  const wrapper = mount(MatrixTable, { props: { compactMode: false, matrixSortMode: 'default' } })
  return { store, wrapper }
}

function congregationCells(wrapper: ReturnType<typeof mount>) {
  return wrapper.findAll('tbody tr').map((tr) => tr.find('td').text())
}

beforeEach(() => {
  setActivePinia(createPinia())
})

describe('MatrixTable congregation filter', () => {
  it('shows all congregations without a query', () => {
    const { wrapper } = mountTable()
    expect(congregationCells(wrapper)).toHaveLength(3)
    expect(wrapper.find('[data-testid="empty-state"]').exists()).toBe(false)
  })

  it('filters rows client-side, ignoring case and umlauts', async () => {
    const { store, wrapper } = mountTable()
    store.congregationQuery = 'zurich'
    await wrapper.vm.$nextTick()
    expect(congregationCells(wrapper)).toEqual([expect.stringContaining('Zürich-Nord')])
  })

  it('offers to reset the filter when nothing matches', async () => {
    const { store, wrapper } = mountTable()
    store.congregationQuery = ' Hamburg '
    await wrapper.vm.$nextTick()

    const empty = wrapper.get('[data-testid="empty-state"]')
    expect(empty.text()).toContain('Keine Gemeinde passt zu „Hamburg“.')
    await empty.get('button').trigger('click')

    expect(store.congregationQuery).toBe('')
    expect(congregationCells(wrapper)).toHaveLength(3)
  })
})

describe('MatrixTable lifecycle review state', () => {
  it('renders the backend review flag in the matrix cell', () => {
    const store = useMatrixStore()
    store.matrix = {
      dates: ['2030-04-14'],
      rows: [{
        congregation_id: 'c',
        congregation_name: 'Gemeinde',
        cells: {
          '2030-04-14': {
            event_id: 'event',
            event_title: 'Gottesdienst',
            category: 'Gottesdienst',
            is_gap: false,
            assignment_id: 'assignment',
            assignment_status: 'ASSIGNED',
            leader_id: 'leader',
            leader_name: 'Ehemalig',
            needs_review: true,
          },
        },
      }],
      holidays: {},
    }
    const wrapper = mount(MatrixTable, {
      props: { compactMode: false, matrixSortMode: 'default' },
    })

    expect(wrapper.text()).toContain('Prüfung erforderlich')
  })
})

describe('MatrixTable planning conflicts', () => {
  const cell = (conflicts: { rule_id: string; severity: 'BLOCK' | 'WARN'; message: string }[]) => ({
    event_id: 'event',
    event_title: 'Gottesdienst',
    category: 'Gottesdienst',
    is_gap: false,
    assignment_id: 'assignment',
    assignment_status: 'ASSIGNED' as const,
    leader_id: 'leader',
    leader_name: 'Pr. Muster',
    conflicts,
  })

  const mountWith = (conflicts: Parameters<typeof cell>[0]) => {
    const store = useMatrixStore()
    store.matrix = {
      dates: ['2030-04-14'],
      rows: [{ congregation_id: 'c', congregation_name: 'Gemeinde', cells: { '2030-04-14': cell(conflicts) } }],
      holidays: {},
    }
    return mount(MatrixTable, { props: { compactMode: false, matrixSortMode: 'default' } })
  }

  it('marks a blocking conflict with its message and a non-colour label', () => {
    const wrapper = mountWith([
      { rule_id: 'no_double_booking', severity: 'BLOCK', message: 'Der Amtsträger ist in einem überlappenden Zeitraum bereits zugewiesen.' },
    ])
    const marker = wrapper.get('[data-testid="cell-conflict"]')
    expect(marker.text()).toContain('Konflikt')
    expect(marker.attributes('title')).toContain('überlappenden Zeitraum')
    expect(marker.classes().join(' ')).toContain('red')
  })

  it('marks short travel time as a warning and lists every message', () => {
    const wrapper = mountWith([
      { rule_id: 'travel_time_check', severity: 'WARN', message: 'Die Wechselzeit zwischen Gemeinden ist zu kurz.' },
    ])
    const marker = wrapper.get('[data-testid="cell-conflict"]')
    expect(marker.text()).toContain('Warnung')
    expect(marker.attributes('title')).toContain('Wechselzeit')
    expect(marker.classes().join(' ')).toContain('amber')
  })

  it('shows the strongest severity when both kinds are present', () => {
    const wrapper = mountWith([
      { rule_id: 'travel_time_check', severity: 'WARN', message: 'Wechselzeit' },
      { rule_id: 'no_double_booking', severity: 'BLOCK', message: 'Doppelt' },
    ])
    const marker = wrapper.get('[data-testid="cell-conflict"]')
    expect(marker.text()).toContain('Konflikt')
    expect(marker.attributes('title')).toContain('Wechselzeit')
    expect(marker.attributes('title')).toContain('Doppelt')
  })

  it('shows nothing without conflicts', () => {
    expect(mountWith([]).find('[data-testid="cell-conflict"]').exists()).toBe(false)
  })
})

describe('MatrixTable scroll shadows', () => {
  it('renders both shadow overlays as decorative elements', () => {
    const { wrapper } = mountTable()
    for (const side of ['left', 'right']) {
      const shadow = wrapper.get(`[data-testid="matrix-shadow-${side}"]`)
      expect(shadow.attributes('aria-hidden')).toBe('true')
      expect(shadow.classes()).toContain('pointer-events-none')
    }
  })

  it('places the left shadow after the sticky congregation column', async () => {
    const { wrapper } = mountTable()
    expect(wrapper.get('[data-testid="matrix-shadow-left"]').attributes('style')).toContain('left: 170px')
    await wrapper.setProps({ compactMode: true })
    expect(wrapper.get('[data-testid="matrix-shadow-left"]').attributes('style')).toContain('left: 120px')
  })
})

describe('MatrixTable sticky horizontal scrollbar', () => {
  it('hides the native scrollbar and renders a sticky proxy at the viewport bottom', () => {
    const { wrapper } = mountTable()
    const scroll = wrapper.get('[data-testid="matrix-scroll"]')
    expect(scroll.classes()).toEqual(expect.arrayContaining(['max-h-[70dvh]', 'overflow-auto', 'overscroll-x-contain', 'overscroll-y-auto']))
    expect(scroll.attributes('tabindex')).toBe('0')
    expect(scroll.attributes('role')).toBe('region')
    const proxy = wrapper.get('[data-testid="matrix-sticky-scrollbar"]')
    expect(proxy.classes()).toEqual(expect.arrayContaining(['sticky', 'bottom-0']))
    expect(proxy.attributes('aria-hidden')).toBe('true')
    expect(proxy.attributes('style')).toContain('width: 0px')
  })

  it('is only shown when the table is wider than its container', async () => {
    const { wrapper } = mountTable()
    // jsdom has no layout: the container fits, so no proxy is needed
    expect(wrapper.get('[data-testid="matrix-sticky-scrollbar"]').attributes('style')).toContain('display: none')
  })
})


describe('MatrixTable sticky date header', () => {
  it('fixes every date heading vertically, congregation cells horizontally and the corner in both directions', () => {
    const { wrapper } = mountTable()
    const corner = wrapper.get('thead th:first-child')
    const date = wrapper.get('thead th:nth-child(2)')
    const congregation = wrapper.get('tbody td:first-child')

    expect(corner.classes()).toEqual(expect.arrayContaining(['sticky', 'top-0', 'left-0', 'z-30']))
    expect(date.classes()).toEqual(expect.arrayContaining(['sticky', 'top-0', 'z-20', 'bg-white', 'dark:bg-gray-900']))
    expect(congregation.classes()).toEqual(expect.arrayContaining(['sticky', 'left-0', 'z-10']))
    expect(wrapper.get('[data-testid="matrix-date-header"]').findAll('th')).toHaveLength(2)
    expect(wrapper.get('[data-testid="matrix-scroll"]').attributes('aria-label')).toContain('vertikal')
    wrapper.unmount()
  })

  it('preserves a solid holiday background and sticky positioning in compact mode', () => {
    const store = useMatrixStore()
    store.matrix = { dates: ['2026-10-04', '2026-10-05'], rows: [row('Stockach')], holidays: { '2026-10-04': ['Erntedank', 'Langer Gedenktag'] } }
    const wrapper = mount(MatrixTable, { props: { compactMode: true, matrixSortMode: 'default' } })
    const holidayHeader = wrapper.get('thead th:nth-child(2)')
    const normalHeader = wrapper.get('thead th:nth-child(3)')
    expect(holidayHeader.classes()).toEqual(expect.arrayContaining(['top-0', 'z-20', 'bg-amber-50', 'dark:bg-amber-950']))
    expect(holidayHeader.text()).toContain('Langer Gedenktag')
    expect(normalHeader.classes()).toEqual(expect.arrayContaining(['top-0', 'bg-white', 'dark:bg-gray-900']))
    expect(wrapper.get('table').classes()).toContain('matrix-table--compact')
    expect(wrapper.get('thead th:first-child').classes()).toContain('px-2')
    wrapper.unmount()
  })

  it('does not create a scrollable header when there are no dates', () => {
    const store = useMatrixStore()
    store.matrix = { dates: [], rows: [], holidays: {} }
    const wrapper = mount(MatrixTable, { props: { compactMode: false, matrixSortMode: 'default' } })
    expect(wrapper.find('[data-testid="matrix-scroll"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Keine Ereignisse im gewählten Zeitraum.')
    wrapper.unmount()
  })
})
