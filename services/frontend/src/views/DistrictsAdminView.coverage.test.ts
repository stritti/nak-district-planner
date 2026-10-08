import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import * as districtsApi from '../api/districts'
import type { CongregationGroupResponse } from '../api/districts'
import DistrictsAdminView from './DistrictsAdminView.vue'

vi.mock('../api/districts')

interface DistrictBindings {
  newGroupName: string
  groupsByDistrict: Record<string, CongregationGroupResponse[]>
  saveGroup: (districtId: string) => Promise<void>
  cancelNewGroup: () => void
  openNewGroup: (districtId: string) => void
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(districtsApi.listDistricts).mockResolvedValue([
    { id: 'd1', name: 'Bezirk Eins', state_code: null, created_at: '', updated_at: '' },
  ])
  vi.mocked(districtsApi.listCongregations).mockResolvedValue([])
  vi.mocked(districtsApi.listGroups).mockResolvedValue([])
})

describe('DistrictsAdminView coverage gaps', () => {
  it('creates and cancels the inline group state without depending on DOM focus', async () => {
    vi.mocked(districtsApi.createGroup).mockResolvedValue({
      id: 'g1',
      district_id: 'd1',
      name: 'Gruppe Neu',
      created_at: '',
      updated_at: '',
    })
    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(DistrictsAdminView, { global: { plugins: [pinia] } })
    await flushPromises()
    const vm = wrapper.vm.$.setupState as DistrictBindings

    vm.newGroupName = ' Gruppe Neu '
    await vm.saveGroup('d1')

    expect(districtsApi.createGroup).toHaveBeenCalledWith('d1', 'Gruppe Neu')
    expect(vm.groupsByDistrict.d1.map((group) => group.name)).toEqual(['Gruppe Neu'])

    vm.newGroupName = 'Abbrechen'
    vm.cancelNewGroup()
    expect(vm.newGroupName).toBe('')

    wrapper.unmount()
    vm.openNewGroup('d1')
    await Promise.resolve()
  })
})
