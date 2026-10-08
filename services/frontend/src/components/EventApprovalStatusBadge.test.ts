import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import EventApprovalStatusBadge from './EventApprovalStatusBadge.vue'

describe('EventApprovalStatusBadge', () => {
  it.each([
    ['PLANNED', 'Geplant', '⏳', 'bg-yellow-100'],
    ['CONFIRMED', 'Bestätigt', '✓', 'bg-green-100'],
  ] as const)('renders %s with its semantic label and style', (status, label, icon, cssClass) => {
    const wrapper = mount(EventApprovalStatusBadge, { props: { status } })

    expect(wrapper.text()).toContain(label)
    expect(wrapper.text()).toContain(icon)
    expect(wrapper.classes()).toContain(cssClass)
  })
})
