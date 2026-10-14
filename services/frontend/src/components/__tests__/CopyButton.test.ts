// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { ref } from 'vue'
import CopyButton from '@/components/CopyButton.vue'

const copied = ref(false)
const copy = vi.fn()

vi.mock('@vueuse/core', () => ({
  useClipboard: vi.fn(() => ({ copy, copied })),
}))

describe('CopyButton', () => {
  beforeEach(() => {
    copied.value = false
    copy.mockReset()
  })

  it('copies the value and confirms success', async () => {
    copy.mockImplementation(async () => {
      copied.value = true
    })
    const wrapper = mount(CopyButton, { props: { value: 'https://example.org/feed.ics' } })

    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(copy).toHaveBeenCalledWith('https://example.org/feed.ics')
    expect(wrapper.text()).toContain('Kopiert!')
    expect(wrapper.emitted('copied')).toEqual([['https://example.org/feed.ics']])
  })

  it('reports failure when no clipboard mechanism is available', async () => {
    copy.mockResolvedValue(undefined)
    const wrapper = mount(CopyButton, { props: { value: 'x' } })

    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Kopieren fehlgeschlagen')
    expect(wrapper.emitted('error')).toHaveLength(1)
    expect(wrapper.emitted('copied')).toBeUndefined()
  })

  it('reports failure when copying throws and recovers on the next attempt', async () => {
    copy.mockRejectedValueOnce(new Error('denied')).mockImplementationOnce(async () => {
      copied.value = true
    })
    const wrapper = mount(CopyButton, { props: { value: 'x' } })

    await wrapper.get('button').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Kopieren fehlgeschlagen')
    expect((wrapper.emitted('error')![0]![0] as Error).message).toBe('denied')

    await wrapper.get('button').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Kopiert!')
    expect(wrapper.text()).not.toContain('fehlgeschlagen')
  })

  it('renders an accessible icon button in icon variant', () => {
    const wrapper = mount(CopyButton, {
      props: { value: 'x', variant: 'icon', label: 'URL kopieren' },
    })
    const button = wrapper.get('button')
    expect(button.attributes('aria-label')).toBe('URL kopieren')
    expect(button.classes()).toContain('btn-icon')
    expect(button.find('svg').exists()).toBe(true)
  })

  it('renders a labelled text button by default', () => {
    const wrapper = mount(CopyButton, { props: { value: 'x' } })
    expect(wrapper.get('button').text()).toBe('Kopieren')
    expect(wrapper.get('[role="status"]').attributes('aria-live')).toBe('polite')
  })
})
