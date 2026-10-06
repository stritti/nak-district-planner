import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import * as districtsApi from '../api/districts'
import DistrictsAdminView from './DistrictsAdminView.vue'

vi.mock('../api/districts')

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(districtsApi.listDistricts).mockResolvedValue([
    { id: 'd1', name: 'Bezirk Eins', state_code: null, created_at: '', updated_at: '' },
  ])
  vi.mocked(districtsApi.listCongregations).mockResolvedValue([])
  vi.mocked(districtsApi.listGroups).mockResolvedValue([])
})

describe('DistrictsAdminView coverage gaps', () => {
  it('creates and cancels the inline group form', async () => {
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

    const groupButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Gruppe')!
    await groupButton.trigger('click')
    const input = wrapper.get('input[placeholder="Name der Gruppe"]')
    await input.setValue(' Gruppe Neu ')
    await input.trigger('keyup.enter')
    await flushPromises()

    expect(districtsApi.createGroup).toHaveBeenCalledWith('d1', 'Gruppe Neu')
    expect(wrapper.text()).toContain('Gruppe Neu')

    await groupButton.trigger('click')
    await wrapper.get('input[placeholder="Name der Gruppe"]').setValue('Abbrechen')
    await wrapper.get('button[title="Abbrechen"]').trigger('click')
    expect(wrapper.find('input[placeholder="Name der Gruppe"]').exists()).toBe(false)
  })
})
