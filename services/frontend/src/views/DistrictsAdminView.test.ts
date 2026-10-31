// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import * as districtsApi from '../api/districts'
import { ApiError } from '../api/errors'
import { useAuthStore } from '../stores/auth'
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
  revision: `"${id}:v1"`,
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
  revision: `"${id}:v1"`,
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
  revision: `"${id}:v1"`,
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

function setup(admin = true) {
  const pinia = createPinia()
  setActivePinia(pinia)
  useAuthStore().isSuperadmin = admin
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
  it('offers to create the first congregation of an empty district', async () => {
    const { wrapper } = setup()
    await flushPromises()

    const empty = wrapper.findAll('[data-testid="empty-state"]').find((node) => node.text().includes('Noch keine Gemeinden.'))!
    await empty.get('button').trigger('click')
    await flushPromises()

    expect(findModal(wrapper, 'Neue Gemeinde').exists()).toBe(true)
  })

  it('offers to create the first district', async () => {
    vi.mocked(districtsApi.listDistricts).mockResolvedValue([])
    const { wrapper } = setup()
    await flushPromises()

    const empty = wrapper.get('[data-testid="empty-state"]')
    expect(empty.text()).toContain('Noch keine Bezirke angelegt.')
    await empty.get('button').trigger('click')
    await flushPromises()

    expect(findModal(wrapper, 'Neuer Bezirk').exists()).toBe(true)
  })

  it('shows a load failure in the shared alert instead of the empty state', async () => {
    vi.mocked(districtsApi.listDistricts).mockRejectedValue(new ApiError(503, 'Unavailable', undefined))
    const { wrapper } = setup()
    await flushPromises()

    const alert = wrapper.get('[data-testid="error-alert"]')
    expect(alert.attributes('role')).toBe('alert')
    expect(alert.text()).toContain('später erneut versuchen')
    expect(wrapper.find('[data-testid="empty-state"]').exists()).toBe(false)
  })

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

  async function editCell(wrapper: ReturnType<typeof mount>, id: string, value: string, key = 'Enter') {
    const cell = wrapper.get(`[data-inline-cell-id="${id}"]`)
    await cell.trigger('click')
    await flushPromises()
    await cell.get('input').setValue(value)
    await cell.get('input').trigger('keydown', { key })
    await flushPromises()
    return cell
  }

  it('renames a district inline with its revision and shows the new name', async () => {
    vi.mocked(districtsApi.updateDistrict).mockResolvedValueOnce({ ...district('d1', 'Neu', 'BW'), revision: '"d1:v2"' })
    const { wrapper } = setup()
    await flushPromises()

    await editCell(wrapper, 'district-name-d1', ' Neu ')

    expect(districtsApi.updateDistrict).toHaveBeenCalledWith('d1', { name: 'Neu' }, '"d1:v1"')
    expect(wrapper.get('[data-inline-cell-id="district-name-d1"]').text()).toContain('Neu')
  })

  it('keeps empty district names and Escape from reaching the API', async () => {
    const { wrapper } = setup()
    await flushPromises()

    const empty = await editCell(wrapper, 'district-name-d1', '   ')
    expect(empty.get('[role="alert"]').text()).toContain('nicht leer')
    await empty.get('input').trigger('keydown', { key: 'Escape' })
    await flushPromises()
    await editCell(wrapper, 'district-name-d1', 'Verworfen', 'Escape')
    expect(districtsApi.updateDistrict).not.toHaveBeenCalled()
    expect(wrapper.get('[data-inline-cell-id="district-name-d1"]').text()).toContain('Bezirk Eins')
  })

  it('offers no rename without the district admin role or a revision', async () => {
    const readOnly = setup(false)
    useAuthStore().memberships = [{ role: 'PLANNER', scope_type: 'DISTRICT', scope_id: 'd1' }] as never
    await flushPromises()
    const planner = readOnly.wrapper.get('[data-inline-cell-id="district-name-d1"]')
    await planner.trigger('click')
    expect(planner.find('input').exists()).toBe(false)
    expect(readOnly.wrapper.get('[data-inline-cell-id="group-name-g1"]').find('input').exists()).toBe(false)

    vi.mocked(districtsApi.listDistricts).mockResolvedValue([{ ...district('d1', 'Bezirk Eins'), revision: undefined }])
    const noRevision = setup()
    await flushPromises()
    const legacy = noRevision.wrapper.get('[data-inline-cell-id="district-name-d1"]')
    await legacy.trigger('click')
    expect(legacy.find('input').exists()).toBe(false)
    expect(districtsApi.updateDistrict).not.toHaveBeenCalled()
  })

  it('keeps the draft on a stale district revision and reloads the current name on request', async () => {
    vi.mocked(districtsApi.updateDistrict).mockRejectedValueOnce(
      new ApiError(412, 'Precondition Failed', { detail: 'Datensatz wurde zwischenzeitlich geändert.' }),
    )
    const { wrapper } = setup()
    await flushPromises()
    const cell = await editCell(wrapper, 'district-name-d1', 'Mein Entwurf')
    expect(cell.get('[role="alert"]').text()).toContain('zwischenzeitlich geändert')
    expect((cell.get('input').element as HTMLInputElement).value).toBe('Mein Entwurf')

    vi.mocked(districtsApi.listDistricts).mockResolvedValue([
      { ...district('d1', 'Bezirk Remote'), revision: '"d1:v9"' }, district('d2', 'Bezirk Zwei'),
    ])
    await cell.get('button').trigger('click')
    await flushPromises()
    expect(cell.get('[role="alert"]').text()).toContain('Aktueller Stand geladen')
    expect((cell.get('input').element as HTMLInputElement).value).toBe('Mein Entwurf')
  })

  it('does not select the district when its name is edited', async () => {
    const { wrapper, districtsStore } = setup()
    await flushPromises()
    districtsStore.setSelectedDistrict('d2')
    await wrapper.get('[data-inline-cell-id="district-name-d1"]').trigger('click')
    expect(districtsStore.selectedDistrictId).toBe('d2')
  })

  it('still selects the district when a user without the admin role clicks its name', async () => {
    const { wrapper, districtsStore } = setup(false)
    useAuthStore().memberships = [{ role: 'PLANNER', scope_type: 'DISTRICT', scope_id: 'd1' }] as never
    await flushPromises()
    districtsStore.setSelectedDistrict('d2')
    const cell = wrapper.get('[data-inline-cell-id="district-name-d1"]')
    await cell.trigger('click')
    expect(cell.find('input').exists()).toBe(false)
    expect(districtsStore.selectedDistrictId).toBe('d1')
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
      '"c1:v1"',
    )

    vi.mocked(districtsApi.updateCongregation).mockRejectedValueOnce('kaputt')
    await wrapper.get('button[title="Gemeinde bearbeiten"]').trigger('click')
    modal = findModal(wrapper, 'Gemeinde bearbeiten')
    await modal.get('input.form-input.mb-4').setValue('Fehler')
    await modal.findAll('button').find((button) => button.text().includes('Speichern'))!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Fehler beim Speichern')
  })

  it('uses the revision of the opened congregation and refreshes after a stale write', async () => {
    vi.mocked(districtsApi.updateCongregation)
      .mockResolvedValueOnce({ ...congregation('c1', 'Erst'), revision: '"c1:v2"' })
      .mockRejectedValueOnce(
        new ApiError(412, 'Precondition Failed', { detail: 'Datensatz wurde zwischenzeitlich geändert.' }),
      )
    const { wrapper } = setup()
    await flushPromises()

    await wrapper.get('button[title="Gemeinde bearbeiten"]').trigger('click')
    let modal = findModal(wrapper, 'Gemeinde bearbeiten')
    await modal.get('input.form-input.mb-4').setValue('Erst')
    await modal.findAll('button').find((button) => button.text().includes('Speichern'))!.trigger('click')
    await flushPromises()

    // The saved row carries the fresh revision, so a second edit is conditional on it.
    vi.mocked(districtsApi.listCongregations).mockResolvedValue([
      { ...congregation('c1', 'Remote'), revision: '"c1:v9"' },
    ])
    await wrapper.get('button[title="Gemeinde bearbeiten"]').trigger('click')
    modal = findModal(wrapper, 'Gemeinde bearbeiten')
    await modal.get('input.form-input.mb-4').setValue('Zweit')
    await modal.findAll('button').find((button) => button.text().includes('Speichern'))!.trigger('click')
    await flushPromises()

    expect(vi.mocked(districtsApi.updateCongregation).mock.calls[1][3]).toBe('"c1:v2"')
    expect(wrapper.text()).toContain('zwischenzeitlich geändert')
    expect(districtsApi.listCongregations).toHaveBeenCalledWith('d1')
    expect(wrapper.text()).toContain('Remote')
  })

  it('shows the server detail when a congregation name is already taken', async () => {
    vi.mocked(districtsApi.updateCongregation).mockRejectedValueOnce(
      new ApiError(409, 'Conflict', { detail: 'Eine Gemeinde mit diesem Namen existiert bereits' }),
    )
    const { wrapper } = setup()
    await flushPromises()

    await wrapper.get('button[title="Gemeinde bearbeiten"]').trigger('click')
    const modal = findModal(wrapper, 'Gemeinde bearbeiten')
    await modal.get('input.form-input.mb-4').setValue('Doppelt')
    await modal.findAll('button').find((button) => button.text().includes('Speichern'))!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Eine Gemeinde mit diesem Namen existiert bereits')
    expect(wrapper.text()).not.toContain('409 Conflict')
  })

  it('renames a group inline with its revision and ignores empty names', async () => {
    vi.mocked(districtsApi.updateGroup).mockResolvedValueOnce({ ...group('g1', 'Gruppe Neu'), revision: '"g1:v2"' })
    const { wrapper } = setup()
    await flushPromises()

    await editCell(wrapper, 'group-name-g1', ' Gruppe Neu ')
    expect(districtsApi.updateGroup).toHaveBeenCalledWith('d1', 'g1', 'Gruppe Neu', '"g1:v1"')
    expect(wrapper.get('[data-inline-cell-id="group-name-g1"]').text()).toContain('Gruppe Neu')

    const empty = await editCell(wrapper, 'group-name-g1', '   ')
    expect(empty.get('[role="alert"]').text()).toContain('nicht leer')
    expect(districtsApi.updateGroup).toHaveBeenCalledTimes(1)
  })

  it('shows the server message and keeps the group name on a stale revision', async () => {
    vi.mocked(districtsApi.updateGroup).mockRejectedValueOnce(
      new ApiError(412, 'Precondition Failed', { detail: 'Datensatz wurde zwischenzeitlich geändert.' }),
    )
    const { wrapper } = setup()
    await flushPromises()
    const cell = await editCell(wrapper, 'group-name-g1', 'Entwurf')
    expect(cell.get('[role="alert"]').text()).toContain('zwischenzeitlich geändert')
    vi.mocked(districtsApi.listGroups).mockResolvedValue([{ ...group('g1', 'Remote'), revision: '"g1:v9"' }])
    await cell.get('button').trigger('click')
    await flushPromises()
    expect(cell.get('[role="alert"]').text()).toContain('Aktueller Stand geladen')
  })

  it('deletes a group, clears local assignments and reports delete failures', async () => {
    vi.mocked(districtsApi.deleteGroup).mockResolvedValue(undefined)
    const { wrapper, toastStore } = setup()
    const success = vi.spyOn(toastStore, 'success')
    await flushPromises()

    const groupRow = wrapper.findAll('div').find((node) => node.text().trim() === 'Gruppe A' && node.find('button').exists())!
    await groupRow.findAll('button')[0].trigger('click')
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
    await secondRow.findAll('button')[0].trigger('click')
    await second.get('[data-test="confirm-delete"]').trigger('click')
    await flushPromises()
    expect(secondError).toHaveBeenCalledWith('Löschen fehlgeschlagen', 'Nicht erlaubt')
  })
})
