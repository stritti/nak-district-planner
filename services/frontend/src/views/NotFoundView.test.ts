// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import NotFoundView from './NotFoundView.vue'

describe('NotFoundView', () => {
  it('shows a useful heading and a link to the event overview', () => {
    const wrapper = mount(NotFoundView, { global: { stubs: ['RouterLink'] } })
    expect(wrapper.text()).toContain('Seite nicht gefunden')
    expect(wrapper.get('router-link-stub').attributes('to')).toBe('/events')
  })
})
