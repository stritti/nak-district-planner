// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import * as districtsApi from '../api/districts'
import { useDistrictsStore } from '../stores/districts'
import { useToastStore } from '../stores/toast'
import DistrictsAdminView from './DistrictsAdminView.vue'

vi.mock('../api/districts')

const now = '2026-10-05T00:00:00Z'

const district = (
  id: string,
  name: string,
  stateCode: string | null = null,
): districtsApi.DistrictResponse => ({
  id,
  name,
  state_code: stateCode,
  created_at: now,
  updated_at: now,
})

const group = (
  id: string,
  name: string,
  districtId = 'd1',
): districtsApi.CongregationGroupResponse => ({
  id,
  name,
  district_id: districtId,
  created_at: now,
  updated_at: now,
})

const congregation = (
  id: string,
  name: string,
  groupId: string | null = null,
  serviceTimes: districtsApi.ServiceTime[] = [],
): districtsApi.CongregationResponse => ({
  id,
  name,
  district_id: 'd1',
  group_id: groupId,
  group_name: groupId ? 'Gruppe A' : null,
  service_times: serviceTimes,
  created_at: now,
  updated_at: now,
})

const ConfirmDialogStub = defineComponent({
  props: { open: Boolean, message: String },
  emits: ['confirm', 'cancel'],
  setup(props, { emit }) {
    return () => props.open
      ? h('div', { 'data-test': 'confirm-dialog' }, [
          h('span', props.message),
          h('button', { 'data-test': 'confirm-delete', onClick: () => emit('confirm') }, 'confirm'),
          h('button', { 'data-test': 'cancel-delete', onClick: () => emit('cancel') }, 'cancel'),
        ])
      : null
  },
})

function findButton(text: string, root: ReturnType<typeof mount>) {
  const button = root.findAll('button').find((node) => node.text().includes(text))
  if (!button) throw new Error(`Button not found: ${text}`)
  return button
}

function findModal(root: ReturnType<typeof mount>, title: string) {
  const modal = root.findAll('.modal-panel').find((node) => node.text().includes(title))
  if (!modal) throw new Error(`Modal not found: ${title}`)
  return modal
}

function setup() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const districtsStore = useDistrictsStore()
  const toastStore = useToastStore()
  const wrapper = mount(DistrictsAdminView, {
    global: {
      plugins: [pinia],
      stubs: { ConfirmDialog: ConfirmDialogStub },
    },
  })
  return { wrapper, districtsStore, toastStore }
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(districtsApi.listDistricts).mockResolvedValue([
    district('d1', 'Bezirk Eins', 'BW'),
    district('d2', 'Bezirk Zwei'),
  ])
  vi.mocked(districtsApi.listCongregations).mockImplementation(async (districtId) => (
    districtId === 'd1'
      ? [
          congregation('c1', 'Gemeinde A', 'g1', [{ weekday: 6, time: '09:30' }]),
          congregation('c2', 'Gemeinde B'),
        ]
      : []
  ))
  vi.mocked(districtsApi.listGroups).mockImplementation(async (districtId) => (
    districtId === 'd1' ? [group('g1', 'Gruppe A')] : []
  ))
})

describe('DistrictsAdminView', () => {
  it('loads districts, groups and congregations and selects a district', async () => {
    const { wrapper, districtsStore } = setup()
    await flushPromises()

    expect(wrapper.text()).toContain('Bezirk Eins')
    expect(wrapper.text()).toContain('BW')
    expect(wrapper.text()).toContain('Gruppe A')
    expect(wrapper.text()).toContain('Gemeinde A')
    expect(wrapper.text()).toContain('So 09:30')
    expect(wrapper.text()).toContain('Noch keine Gemeinden.')
    expect(districtsStore.selectedDistrictId).toBe('d1')

    const districtHeaders = wrapper.findAll('.card > div').filter((node) => node.text().includes('Bezirk Zwei'))
    await districtHeaders[0].trigger('click')
    expect(districtsStore.selectedDistrictId).toBe('d2')
  })

  it('surfaces top-level load errors and tolerates one district child-load failure', async () => {
    vi.mocked(districtsApi.listDistricts).mockRejectedValueOnce(new Error('Bezirke kaputt'))
    const first = setup().wrapper
    await flushPromises()
    expect(first.text()).toContain('Bezirke kaputt')

    vi.mocked(districtsApi.listDistricts).mockResolvedValueOnce([district('d1', 'Bezirk Eins')])
    vi.mocked(districtsApi.listCongregations).mockRejectedValueOnce(new Error('Gemeinden kaputt'))
    const second = setup().wrapper
    await flushPromises()
    expect(second.text()).toContain('Bezirk Eins')
    expect(second.text()).toContain('Noch keine Gemeinden.')
  })

  it('creates a district and renders provider errors without mutating the list', async () => {
    vi.mocked(districtsApi.createDistrict).mockResolvedValueOnce(district('d3', 'Bezirk Drei', 'BY'))
    const { wrapper } = setup()
    await flushPromises()

    await findButton('Neuer Bezirk', wrapper).trigger('click')
    let modal = findModal(wrapper, 'Neuer Bezirk')
    await modal.get('input[placeholder="z. B. Bezirk Nord"]').setValue(' Bezirk Drei ')
    await modal.get('select').setValue('BY')
    await findButton('Anlegen', modal as unknown as ReturnType<typeof mount>).trigger('click')
    await flushPromises()

    expect(districtsApi.createDistrict).toHaveBeenCalledWith('Bezirk Drei', 'BY')
    expect(wrapper.text()).toContain('Bezirk Drei')

    vi.mocked(districtsApi.createDistrict).mockRejectedValueOnce('kaputt')
    await findButton('Neuer Bezirk', wrapper).trigger('click')
    modal = findModal(wrapper, 'Neuer Bezirk')
    await modal.get('input[placeholder="z. B. Bezirk Nord"]').setValue('Fehlerbezirk')
    await findButton('Anlegen', modal as unknown as ReturnType<typeof mount>).trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Fehler')
  })

  it('renames a district and keeps empty edits from reaching the API', async () => {
    vi.mocked(districtsApi.updateDistrict).mockResolvedValueOnce(district('d1', 'Neu', 'BW'))
    const { wrapper } = setup()
    await flushPromises()

    await wrapper.get('button[title="Bezirk umbenennen"]').trigger('click')
    const input = wrapper.get('input.form-input.w-56')
    await input.setValue(' Neu ')
    await wrapper.get('button[title="Speichern"]').trigger('click')
    await flushPromises()

    expect(districtsApi.updateDistrict).toHaveBeenCalledWith('d1', { name: 'Neu' })
    expect(wrapper.text()).toContain('Neu')

    await wrapper.get('button[title="Bezirk umbenennen"]').trigger('click')
    await wrapper.get('input.form-input.w-56').setValue('   ')
    await wrapper.get('input.form-input.w-56').trigger('keyup.enter')
    expect(districtsApi.updateDistrict).toHaveBeenCalledTimes(1)
    await wrapper.get('input.form-input.w-56').trigger('keyup.escape')
  })

  it('creates a congregation with a service time and reports create errors', async () => {
    vi.mocked(districtsApi.createCongregation).mockResolvedValueOnce(
      congregation('c3', 'Gemeinde C', 'g1', [{ weekday: 6, time: '10:00' }]),
    )
    const { wrapper } = setup()
    await flushPromises()

    const congregationButton = wrapper.findAll('button').find((button) => button.text().includes('Gemeinde'))!
    await congregationButton.trigger('click')
    let modal = findModal(wrapper, 'Neue Gemeinde')
    await modal.get('input[placeholder="z. B. Gemeinde Mitte"]').setValue(' Gemeinde C ')
    await modal.get('select.form-input').setValue('g1')
    await modal.findAll('button').find((button) => button.text().includes('Hinzufuegen'))!.trigger('click')
    const time = modal.get('input[type="time"]')
    await time.setValue('10:00')
    await modal.findAll('button').find((button) => button.text().includes('Anlegen'))!.trigger('click')
    await flushPromises()

    expect(districtsApi.createCongregation).toHaveBeenCalledWith(
      'd1',
      'Gemeinde C',
      [{ weekday: 6, time: '10:00' }],
      'g1',
    )
    expect(wrapper.text()).toContain('Gemeinde C')

    vi.mocked(districtsApi.createCongregation).mockRejectedValueOnce(new Error('Anlegen fehlgeschlagen'))
    await congregationButton.trigger('click')
    modal = findModal(wrapper, 'Neue Gemeinde')
    await modal.get('input[placeholder="z. B. Gemeinde Mitte"]').setValue('Fehler')
    await modal.findAll('button').find((button) => button.text().includes('Anlegen'))!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Anlegen fehlgeschlagen')
  })

  it('edits a congregation including service times and surfaces update failures', async () => {
    vi.mocked(districtsApi.updateCongregation).mockResolvedValueOnce(
      congregation('c1', 'Gemeinde Neu', null, [{ weekday: 0, time: '19:30' }]),
    )
    const { wrapper } = setup()
    await flushPromises()

    await wrapper.get('button[title="Gemeinde bearbeiten"]').trigger('click')
    let modal = findModal(wrapper, 'Gemeinde bearbeiten')
    await modal.get('input.form-input.mb-4').setValue(' Gemeinde Neu ')
    await modal.get('select.form-input').setValue('')
    await modal.findAll('button').find((button) => button.text().includes('Hinzufügen'))!.trigger('click')
    const times = modal.findAll('input[type="time"]')
    await times[0].setValue('19:30')
    await modal.findAll('button[title="Entfernen"]')[1].trigger('click')
    await modal.findAll('button').find((button) => button.text().includes('Speichern'))!.trigger('click')
    await flushPromises()

    expect(districtsApi.updateCongregation).toHaveBeenCalledWith(
      'd1',
      'c1',
      expect.objectContaining({ name: 'Gemeinde Neu', group_id: null }),
    )

    vi.mocked(districtsApi.updateCongregation).mockRejectedValueOnce('kaputt')
    await wrapper.get('button[title="Gemeinde bearbeiten"]').trigger('click')
    modal = findModal(wrapper, 'Gemeinde bearbeiten')
    await modal.get('input.form-input.mb-4').setValue('Fehler')
    await modal.findAll('button').find((button) => button.text().includes('Speichern'))!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Fehler beim Speichern')
  })

  it('renames a group and ignores empty names', async () => {
    vi.mocked(districtsApi.updateGroup).mockResolvedValueOnce(group('g1', 'Gruppe Neu'))
    const { wrapper } = setup()
    await flushPromises()

    const groupRow = wrapper.findAll('div').find((node) => node.text().trim() === 'Gruppe A' && node.findAll('button').length === 2)!
    await groupRow.findAll('button')[0].trigger('click')
    const editGroupInput = wrapper.get('input.form-input.w-40')
    await editGroupInput.setValue(' Gruppe Neu ')
    await editGroupInput.trigger('keyup.enter')
    await flushPromises()
    expect(districtsApi.updateGroup).toHaveBeenCalledWith('d1', 'g1', 'Gruppe Neu')

    const renamedRow = wrapper.findAll('div').find((node) => node.text().trim() === 'Gruppe Neu' && node.findAll('button').length === 2)!
    await renamedRow.findAll('button')[0].trigger('click')
    await wrapper.get('input.form-input.w-40').setValue('   ')
    await wrapper.get('input.form-input.w-40').trigger('keyup.enter')
    expect(districtsApi.updateGroup).toHaveBeenCalledTimes(1)
    await wrapper.get('input.form-input.w-40').trigger('keyup.escape')
  })

  it('deletes a group, clears local assignments and reports delete failures', async () => {
    vi.mocked(districtsApi.deleteGroup).mockResolvedValue(undefined)
    const { wrapper, toastStore } = setup()
    const success = vi.spyOn(toastStore, 'success')
    await flushPromises()

    const groupRow = wrapper.findAll('div').find((node) => node.text().trim() === 'Gruppe A' && node.find('button').exists())!
    await groupRow.findAll('button')[1].trigger('click')
    expect(wrapper.find('[data-test="confirm-dialog"]').exists()).toBe(true)
    await wrapper.get('[data-test="confirm-delete"]').trigger('click')
    await flushPromises()

    expect(districtsApi.deleteGroup).toHaveBeenCalledWith('d1', 'g1')
    expect(success).toHaveBeenCalledWith('Gruppe gelöscht', 'Gruppe A')

    vi.mocked(districtsApi.deleteGroup).mockRejectedValueOnce(new Error('Nicht erlaubt'))
    vi.mocked(districtsApi.listGroups).mockResolvedValueOnce([group('g3', 'Gruppe C')])
    vi.mocked(districtsApi.listCongregations).mockResolvedValueOnce([])
    vi.mocked(districtsApi.listDistricts).mockResolvedValueOnce([district('d1', 'Bezirk Eins')])
    const secondSetup = setup()
    const secondError = vi.spyOn(secondSetup.toastStore, 'error')
    const second = secondSetup.wrapper
    await flushPromises()
    const secondRow = second.findAll('div').find((node) => node.text().trim() === 'Gruppe C' && node.find('button').exists())!
    await secondRow.findAll('button')[1].trigger('click')
    await second.get('[data-test="confirm-delete"]').trigger('click')
    await flushPromises()
    expect(secondError).toHaveBeenCalledWith('Löschen fehlgeschlagen', 'Nicht erlaubt')
  })
})
