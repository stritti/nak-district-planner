// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import MatrixSkeleton from '@/components/MatrixSkeleton.vue'

describe('MatrixSkeleton', () => {
  it('announces loading to assistive technology', () => {
    const wrapper = mount(MatrixSkeleton)
    const root = wrapper.get('[role="status"]')
    expect(root.attributes('aria-busy')).toBe('true')
    expect(root.text()).toContain('Dienstplan wird geladen')
  })

  it('renders the default number of placeholder rows', () => {
    expect(mount(MatrixSkeleton).findAll('[data-testid="matrix-skeleton-row"]')).toHaveLength(6)
  })

  it('renders the requested rows and columns', () => {
    const wrapper = mount(MatrixSkeleton, { props: { rows: 2, columns: 3 } })
    const rows = wrapper.findAll('[data-testid="matrix-skeleton-row"]')
    expect(rows).toHaveLength(2)
    // label cell + one placeholder per column
    expect(rows[0]!.findAll('div')).toHaveLength(4)
  })
})
