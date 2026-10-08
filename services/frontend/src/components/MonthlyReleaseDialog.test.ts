import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import * as eventsApi from '../api/events'
import MonthlyReleaseDialog from './MonthlyReleaseDialog.vue'

vi.mock('../api/events')

function mountDialog() {
  return mount(MonthlyReleaseDialog, {
    props: { open: false, districtId: 'district-1' },
  })
}

describe('MonthlyReleaseDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(eventsApi.listEvents).mockResolvedValue({ items: [], total: 2 })
  })

  it('loads the current month count when opened and emits close on cancel', async () => {
    const wrapper = mountDialog()

    await wrapper.setProps({ open: true })
    await flushPromises()

    expect(eventsApi.listEvents).toHaveBeenCalledWith(expect.objectContaining({
      district_id: 'district-1',
      approval_status: 'PLANNED',
      limit: 1,
      offset: 0,
    }))
    expect(wrapper.text()).toContain('2 Termine')

    await wrapper.get('button.btn-secondary').trigger('click')
    expect(wrapper.emitted('close')).toHaveLength(1)
  })

  it('shows the already-released state and disables confirmation for zero planned events', async () => {
    vi.mocked(eventsApi.listEvents).mockResolvedValue({ items: [], total: 0 })
    const wrapper = mountDialog()

    await wrapper.setProps({ open: true })
    await flushPromises()

    expect(wrapper.text()).toContain('bereits bestätigt')
    expect(wrapper.get('button.btn-primary').attributes('disabled')).toBeDefined()
  })

  it('fails closed to zero planned events when counting fails', async () => {
    vi.mocked(eventsApi.listEvents).mockRejectedValue(new Error('network'))
    const wrapper = mountDialog()

    await wrapper.setProps({ open: true })
    await flushPromises()

    expect(wrapper.text()).toContain('bereits bestätigt')
  })

  it('recounts when the selected month changes while open', async () => {
    const wrapper = mountDialog()
    await wrapper.setProps({ open: true })
    await flushPromises()
    vi.mocked(eventsApi.listEvents).mockClear()

    const select = wrapper.get('select')
    const values = select.findAll('option').map((option) => option.attributes('value'))
    const current = (select.element as HTMLSelectElement).value
    const alternative = values.find((value) => value && value !== current)!
    await select.setValue(alternative)
    await flushPromises()

    expect(eventsApi.listEvents).toHaveBeenCalledOnce()
  })

  it('confirms the selected month and emits the updated count', async () => {
    vi.mocked(eventsApi.bulkUpdateApprovalStatus).mockResolvedValue({ updated_count: 3 })
    const wrapper = mountDialog()
    await wrapper.setProps({ open: true })
    await flushPromises()

    await wrapper.get('button.btn-primary').trigger('click')
    await flushPromises()

    expect(eventsApi.bulkUpdateApprovalStatus).toHaveBeenCalledWith(
      'district-1',
      expect.objectContaining({ approval_status: 'CONFIRMED' }),
    )
    expect(wrapper.emitted('released')).toEqual([[3]])
  })

  it('recovers from release errors without emitting success', async () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.mocked(eventsApi.bulkUpdateApprovalStatus).mockRejectedValue(new Error('failed'))
    const wrapper = mountDialog()
    await wrapper.setProps({ open: true })
    await flushPromises()

    await wrapper.get('button.btn-primary').trigger('click')
    await flushPromises()

    expect(wrapper.emitted('released')).toBeUndefined()
    expect(errorSpy).toHaveBeenCalled()
    expect(wrapper.get('button.btn-primary').attributes('disabled')).toBeUndefined()
  })
})
