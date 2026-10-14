// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ApplicabilitySelect from '@/components/ApplicabilitySelect.vue'

const congregations = [
  { id: 'c1', name: 'Gemeinde Nord' },
  { id: 'c2', name: 'Gemeinde Süd' },
  { id: 'c3', name: 'Gemeinde West' },
]

function mountWith(modelValue: string[], extra: Record<string, unknown> = {}) {
  return mount(ApplicabilitySelect, { props: { modelValue, congregations, ...extra } })
}

function lastEmitted(wrapper: ReturnType<typeof mountWith>): string[] {
  const events = wrapper.emitted('update:modelValue')
  expect(events).toBeDefined()
  return events!.at(-1)![0] as string[]
}

describe('ApplicabilitySelect', () => {
  it('renders one checkbox per congregation and nothing checked for an undistributed event', () => {
    const wrapper = mountWith([])
    expect(wrapper.text()).toContain('Gemeinde Nord')
    expect(wrapper.findAll('input[type="checkbox"]')).toHaveLength(4)
    expect(wrapper.findAll('input:checked')).toHaveLength(0)
  })

  it('selecting "all" emits the backend sentinel', async () => {
    const wrapper = mountWith([])
    await wrapper.get('[data-testid="applicability-all"]').setValue(true)
    expect(lastEmitted(wrapper)).toEqual(['all'])
  })

  it('shows every congregation as checked but disabled while "all" is selected', () => {
    const wrapper = mountWith(['all'])
    const single = wrapper.get('[data-testid="applicability-c2"]')
    expect((single.element as HTMLInputElement).checked).toBe(true)
    expect(single.attributes('disabled')).toBeDefined()
  })

  it('unselecting "all" clears the distribution', async () => {
    const wrapper = mountWith(['all'])
    await wrapper.get('[data-testid="applicability-all"]').setValue(false)
    expect(lastEmitted(wrapper)).toEqual([])
  })

  it('adds congregations in list order regardless of click order', async () => {
    const wrapper = mountWith(['c3'])
    await wrapper.get('[data-testid="applicability-c1"]').setValue(true)
    expect(lastEmitted(wrapper)).toEqual(['c1', 'c3'])
  })

  it('removes a congregation and drops IDs of congregations that no longer exist', async () => {
    const wrapper = mountWith(['c1', 'deleted-congregation', 'c2'])
    await wrapper.get('[data-testid="applicability-c1"]').setValue(false)
    expect(lastEmitted(wrapper)).toEqual(['c2'])
  })

  it('omits the congregation list while congregations are still loading', () => {
    const wrapper = mount(ApplicabilitySelect, { props: { modelValue: [], congregations: [] } })
    expect(wrapper.findAll('input[type="checkbox"]')).toHaveLength(1)
  })

  it('disables the whole selection when requested', () => {
    const wrapper = mountWith([], { disabled: true })
    expect(wrapper.get('fieldset').attributes('disabled')).toBeDefined()
  })
})
