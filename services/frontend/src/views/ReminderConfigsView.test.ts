import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import * as districtsApi from '../api/districts'
import ReminderConfigsView from './ReminderConfigsView.vue'

vi.mock('../api/districts')

function mountView() {
  return mount(ReminderConfigsView, {
    global: {
      stubs: {
        ReminderConfigsPanel: { props: ['districtId'], template: '<div data-test="reminders">{{ districtId }}</div>' },
        EventHooksPanel: { props: ['districtId'], template: '<div data-test="hooks">{{ districtId }}</div>' },
      },
    },
  })
}

beforeEach(() => vi.clearAllMocks())

describe('ReminderConfigsView', () => {
  it('selects the first district and renders both district-scoped panels', async () => {
    vi.mocked(districtsApi.listDistricts).mockResolvedValue([
      { id: 'd1', name: 'Bezirk Eins' },
      { id: 'd2', name: 'Bezirk Zwei' },
    ] as districtsApi.DistrictResponse[])

    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.get('select').element.value).toBe('d1')
    expect(wrapper.get('[data-test="reminders"]').text()).toBe('d1')
    expect(wrapper.get('[data-test="hooks"]').text()).toBe('d1')

    await wrapper.get('select').setValue('d2')
    expect(wrapper.get('[data-test="reminders"]').text()).toBe('d2')
    expect(wrapper.get('[data-test="hooks"]').text()).toBe('d2')
  })

  it('keeps panels hidden when no district exists', async () => {
    vi.mocked(districtsApi.listDistricts).mockResolvedValue([])

    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.find('[data-test="reminders"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="hooks"]').exists()).toBe(false)
  })

  it('shows Error and non-Error loading failures', async () => {
    vi.mocked(districtsApi.listDistricts).mockRejectedValueOnce(new Error('Bezirke kaputt'))
    const errorWrapper = mountView()
    await flushPromises()
    expect(errorWrapper.get('[role="alert"]').text()).toBe('Bezirke kaputt')

    vi.mocked(districtsApi.listDistricts).mockRejectedValueOnce('unknown')
    const fallbackWrapper = mountView()
    await flushPromises()
    expect(fallbackWrapper.get('[role="alert"]').text()).toBe('Bezirke konnten nicht geladen werden')
  })
})
