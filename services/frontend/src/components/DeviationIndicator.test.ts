import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import DeviationIndicator from './DeviationIndicator.vue'

describe('DeviationIndicator', () => {
  it('renders nothing without a deviation', () => {
    const wrapper = mount(DeviationIndicator)
    expect(wrapper.find('.deviation-indicator-group').exists()).toBe(false)
  })

  it('renders planned and actual values plus positive and negative differences', () => {
    const wrapper = mount(DeviationIndicator, {
      props: {
        hasDeviation: true,
        plannedTime: '10:00–11:00',
        actualTime: '10:05–10:55',
        startDiffMinutes: 5,
        endDiffMinutes: -5,
      },
    })

    expect(wrapper.text()).toContain('Geplant:')
    expect(wrapper.text()).toContain('10:00–11:00')
    expect(wrapper.text()).toContain('Tatsächlich:')
    expect(wrapper.text()).toContain('10:05–10:55')
    expect(wrapper.text()).toContain('+5 Min.')
    expect(wrapper.text()).toContain('(Ende: -5 Min.)')
  })

  it('supports compact rendering and zero-minute differences', () => {
    const wrapper = mount(DeviationIndicator, {
      props: {
        hasDeviation: true,
        startDiffMinutes: 0,
        endDiffMinutes: 0,
        compact: true,
      },
    })

    expect(wrapper.get('.deviation-indicator-group').classes()).toContain(
      'deviation-indicator-group-compact',
    )
    expect(wrapper.get('.deviation-icon').classes()).toContain('deviation-icon-compact')
    expect(wrapper.get('.deviation-tooltip').classes()).toContain('deviation-tooltip-compact')
    expect(wrapper.text()).toContain('0 Min.')
    expect(wrapper.text()).toContain('(Ende: 0 Min.)')
  })

  it('renders only the available difference value', async () => {
    const wrapper = mount(DeviationIndicator, {
      props: { hasDeviation: true, startDiffMinutes: null, endDiffMinutes: 7 },
    })
    expect(wrapper.text()).not.toContain(' Min. (Ende:')
    expect(wrapper.text()).toContain('(Ende: +7 Min.)')

    await wrapper.setProps({ startDiffMinutes: -2, endDiffMinutes: null })
    expect(wrapper.text()).toContain('-2 Min.')
    expect(wrapper.text()).not.toContain('Ende:')
  })
})
