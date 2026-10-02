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
