// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import ErrorAlert from '../ErrorAlert.vue'

describe('ErrorAlert', () => {
  it('announces the message as an alert', () => {
    const wrapper = mount(ErrorAlert, { props: { message: 'Für diese Aktion fehlt die Berechtigung.' } })
    const alert = wrapper.get('[data-testid="error-alert"]')
    expect(alert.attributes('role')).toBe('alert')
    expect(alert.text()).toBe('Für diese Aktion fehlt die Berechtigung.')
  })

  it('renders nothing without a message', () => {
    for (const message of [undefined, null, '']) {
      expect(mount(ErrorAlert, { props: { message } }).find('[data-testid="error-alert"]').exists()).toBe(false)
    }
  })

  it('takes extra spacing classes from the caller', () => {
    const wrapper = mount(ErrorAlert, { props: { message: 'x' }, attrs: { class: 'mt-3' } })
    expect(wrapper.get('[data-testid="error-alert"]').classes()).toContain('mt-3')
  })
})
