// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import MatrixFilters from '@/components/MatrixFilters.vue'
import { useMatrixStore } from '@/stores/matrix'
import { useDistrictsStore } from '@/stores/districts'
import { useToastStore } from '@/stores/toast'
import { exportMatrixToExcel } from '@/composables/useExcelExport'

vi.mock('@/api/matrix')
vi.mock('@/composables/useExcelExport', () => ({ exportMatrixToExcel: vi.fn() }))

function mountFilters() {
  const store = useMatrixStore()
  store.districtId = 'd1'
  store.fromDt = '2020-01-05' // deliberately no preset range
  store.toDt = '2020-01-20'
  const wrapper = mount(MatrixFilters, {
    props: { compactMode: false, matrixSortMode: 'default' },
  })
  return { store, toasts: useToastStore(), wrapper }
}

function button(wrapper: ReturnType<typeof mount>, label: string) {
  const found = wrapper.findAll('button').find((b) => b.text().includes(label))
  if (!found) throw new Error(`button ${label} not found`)
  return found
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('MatrixFilters', () => {
  it('binds the congregation text filter to the store', async () => {
    const { store, wrapper } = mountFilters()
    await wrapper.get('input[name="congregation-filter"]').setValue('Bern')
    expect(store.congregationQuery).toBe('Bern')
  })

  it('reports generated drafts as a success toast', async () => {
    const { store, toasts, wrapper } = mountFilters()
    vi.spyOn(store, 'generateDraftsForCurrentRange').mockResolvedValue({
      created: 3,
      skipped_existing: 1,
      generated_in_requested_range: 4,
    } as Awaited<ReturnType<typeof store.generateDraftsForCurrentRange>>)

    await button(wrapper, 'Entwuerfe erzeugen').trigger('click')
    await flushPromises()

    expect(toasts.messages).toEqual([
      expect.objectContaining({
        type: 'success',
        title: 'Entwürfe erzeugt',
        message: 'Neu: 3, bereits vorhanden: 1, im Bereich vorhanden: 4',
      }),
    ])
  })

  it('reports a failed draft generation as an error toast', async () => {
    const { store, toasts, wrapper } = mountFilters()
    vi.spyOn(store, 'generateDraftsForCurrentRange').mockRejectedValue(new Error('403 Forbidden'))

    await button(wrapper, 'Entwuerfe erzeugen').trigger('click')
    await flushPromises()

    expect(toasts.messages).toEqual([
      expect.objectContaining({ type: 'error', message: '403 Forbidden' }),
    ])
    expect(button(wrapper, 'Entwuerfe erzeugen').attributes('disabled')).toBeUndefined()
  })

  it('reports a failed Excel export instead of failing silently', async () => {
    const { store, toasts, wrapper } = mountFilters()
    store.matrix = { dates: ['2026-10-04'], rows: [], holidays: {} }
    vi.mocked(exportMatrixToExcel).mockRejectedValue(new Error('quota exceeded'))
    await wrapper.vm.$nextTick() // the button is enabled once a matrix is loaded

    await button(wrapper, 'Excel').trigger('click')
    await flushPromises()

    expect(toasts.messages).toEqual([
      expect.objectContaining({ type: 'error', title: 'Excel-Export fehlgeschlagen' }),
    ])
  })

  it('switches the date range via presets and refetches', async () => {
    const { store, wrapper } = mountFilters()
    const fetch = vi.spyOn(store, 'fetch').mockResolvedValue()

    await button(wrapper, 'Kommender Monat').trigger('click')
    expect(button(wrapper, 'Kommender Monat').classes()).toContain('bg-blue-600')
    await button(wrapper, 'Aktueller Monat').trigger('click')

    expect(button(wrapper, 'Aktueller Monat').classes()).toContain('bg-blue-600')
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('marks no preset for a custom range', () => {
    const { wrapper } = mountFilters()
    for (const label of ['Aktueller Monat', 'Kommender Monat']) {
      expect(button(wrapper, label).classes()).not.toContain('bg-blue-600')
    }
  })

  it('fetches the matrix on "Anzeigen"', async () => {
    const { store, wrapper } = mountFilters()
    const fetch = vi.spyOn(store, 'fetch').mockResolvedValue()
    await button(wrapper, 'Anzeigen').trigger('click')
    expect(fetch).toHaveBeenCalledOnce()
  })

  it('emits view option changes and the release request', async () => {
    const { wrapper } = mountFilters()

    await wrapper.findAll('select').at(-1)!.setValue('grouped')
    await button(wrapper, 'Kompakt').trigger('click')
    await button(wrapper, 'Normal').trigger('click')
    await button(wrapper, 'Freigabe').trigger('click')

    expect(wrapper.emitted('update:matrixSortMode')).toEqual([['grouped']])
    expect(wrapper.emitted('update:compactMode')).toEqual([[true], [false]])
    expect(wrapper.emitted('release')).toHaveLength(1)
  })

  it('writes the date range and group filter to the store', async () => {
    const districts = useDistrictsStore()
    districts.groups = [{ id: 'g1', name: 'Ring A' }] as typeof districts.groups
    const { store, wrapper } = mountFilters()
    const fetch = vi.spyOn(store, 'fetch').mockResolvedValue()

    const [from, to] = wrapper.findAll('input[type="date"]')
    await from!.setValue('2020-02-01')
    await to!.setValue('2020-02-29')
    await wrapper.findAll('select').find((sel) => sel.text().includes('Alle Gruppen'))!.setValue('g1')

    expect([store.fromDt, store.toDt, store.groupId]).toEqual(['2020-02-01', '2020-02-29', 'g1'])
    expect(fetch).toHaveBeenCalledOnce()
  })
})

