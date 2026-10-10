// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { CalendarDaysIcon } from '@heroicons/vue/24/outline'
import EmptyState from '@/components/EmptyState.vue'

describe('EmptyState', () => {
  it('renders the message without optional parts', () => {
    const wrapper = mount(EmptyState, { props: { message: 'Keine Ereignisse gefunden.' } })
    expect(wrapper.text()).toBe('Keine Ereignisse gefunden.')
    expect(wrapper.find('svg').exists()).toBe(false)
    expect(wrapper.find('button').exists()).toBe(false)
  })

  it('renders icon and hint', () => {
    const wrapper = mount(EmptyState, {
      props: { message: 'Leer', hint: 'Filter anpassen', icon: CalendarDaysIcon },
    })
    expect(wrapper.find('svg').attributes('aria-hidden')).toBe('true')
    expect(wrapper.text()).toContain('Filter anpassen')
  })

  it('emits action from the call-to-action button', async () => {
    const wrapper = mount(EmptyState, { props: { message: 'Leer', actionLabel: 'Anlegen' } })
    await wrapper.get('button').trigger('click')
    expect(wrapper.emitted('action')).toHaveLength(1)
  })

  it('uses reduced spacing in compact mode', () => {
    const wrapper = mount(EmptyState, { props: { message: 'Leer', compact: true } })
    expect(wrapper.get('[data-testid="empty-state"]').classes()).toContain('py-3')
  })
})
