// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import NotFoundView from './NotFoundView'

describe('NotFoundView', () => {
  it('shows a useful heading and a link to the event overview', () => {
    const wrapper = mount(NotFoundView)
    expect(wrapper.get('[data-testid="not-found-page"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Seite nicht gefunden')
    expect(wrapper.get('a').attributes('href')).toBe('/events')
  })
})
