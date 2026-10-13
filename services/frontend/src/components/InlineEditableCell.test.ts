// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import InlineEditableCell from './InlineEditableCell.vue'
import { useInlineCellCoordinator } from '../composables/useInlineCellCoordinator'
import { ApiError } from '../api/errors'

function setup(override: Record<string, unknown> = {}) {
  const save = vi.fn(async () => undefined)
  const coordinator = useInlineCellCoordinator()
  const wrapper = mount(InlineEditableCell, {
    attachTo: document.body,
    props: {
      id: 'cell-1', value: 'Vorher', revision: '"rev-1"', label: 'Titel',
      editable: true, coordinator, save, required: true, maxLength: 500,
      ...override,
    },
  })
  return { wrapper, save, coordinator }
}

async function open(wrapper: ReturnType<typeof setup>['wrapper']) {
  await wrapper.trigger('click')
  await flushPromises()
}

afterEach(() => { document.body.replaceChildren() })

describe('InlineEditableCell', () => {
  it('shows a compact full-value read mode without permanent input', () => {
    const { wrapper } = setup()
    expect(wrapper.find('input').exists()).toBe(false)
    expect(wrapper.get('span').attributes('title')).toBe('Vorher')
    expect(wrapper.attributes('tabindex')).toBe('0')
  })

  it('does not activate a forbidden field or send a request', async () => {
    const { wrapper, save } = setup({ editable: false })
    await wrapper.trigger('click')
    await wrapper.trigger('keydown', { key: 'Enter' })
    expect(wrapper.find('input').exists()).toBe(false)
    expect(save).not.toHaveBeenCalled()
    expect(wrapper.attributes('tabindex')).toBeUndefined()
  })

  it.each(['Enter', 'F2'])('activates and focuses from keyboard %s', async (key) => {
    const { wrapper } = setup()
    await wrapper.trigger('keydown', { key })
    await flushPromises()
    expect(wrapper.get('input').element).toBe(document.activeElement)
  })

  it('activates from click and cancels Escape without mutation', async () => {
    const { wrapper, save } = setup()
    await open(wrapper)
    await wrapper.get('input').setValue('Entwurf')
    await wrapper.get('input').trigger('keydown', { key: 'Escape' })
    expect(wrapper.find('input').exists()).toBe(false)
    expect(wrapper.text()).toContain('Vorher')
    expect(save).not.toHaveBeenCalled()
  })

  it('saves a changed value with Enter and the captured revision', async () => {
    const { wrapper, save } = setup()
    await open(wrapper)
    await wrapper.get('input').setValue('   Neu   ')
    await wrapper.get('input').trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(save).toHaveBeenCalledOnce()
    expect(save).toHaveBeenCalledWith('Neu', '"rev-1"')
  })

  it('never persists unchanged data', async () => {
    const { wrapper, save } = setup()
    await open(wrapper)
    await wrapper.get('input').trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(save).not.toHaveBeenCalled()
    expect(wrapper.find('input').exists()).toBe(false)
  })

  it('validates empty input while retaining draft', async () => {
    const { wrapper, save } = setup()
    await open(wrapper)
    await wrapper.get('input').setValue('   ')
    await wrapper.get('input').trigger('keydown', { key: 'Enter' })
    expect(wrapper.get('[role="alert"]').text()).toContain('nicht leer')
    expect(wrapper.get('input').exists()).toBe(true)
    expect(save).not.toHaveBeenCalled()
  })

  it('rejects overlong input even if set programmatically', async () => {
    const { wrapper, save } = setup({ maxLength: 3 })
    await open(wrapper)
    await wrapper.get('input').setValue('ZuLang')
    await wrapper.get('input').trigger('keydown', { key: 'Enter' })
    expect(wrapper.get('[role="alert"]').text()).toContain('zu lang')
    expect(save).not.toHaveBeenCalled()
  })

  it('saves on leaving the cell', async () => {
    const { wrapper, save } = setup()
    await open(wrapper)
    await wrapper.get('input').setValue('Neu')
    await wrapper.get('input').trigger('focusout', { relatedTarget: document.body })
    await flushPromises()
    expect(save).toHaveBeenCalledOnce()
  })

  it('does not save when focus remains within the cell', async () => {
    const { wrapper, save } = setup()
    await open(wrapper)
    await wrapper.get('input').setValue('Neu')
    await wrapper.get('input').trigger('focusout', { relatedTarget: wrapper.element })
    expect(save).not.toHaveBeenCalled()
  })

  it('keeps stale snapshot revision after refreshed props', async () => {
    const { wrapper, save } = setup()
    await open(wrapper)
    await wrapper.setProps({ value: 'Fremde Änderung', revision: '"rev-2"' })
    await wrapper.get('input').setValue('Eigene Änderung')
    await wrapper.get('input').trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(save).toHaveBeenCalledWith('Eigene Änderung', '"rev-1"')
  })

  it('does not issue overlapping requests when Enter is pressed twice', async () => {
    let resolve!: () => void
    const save = vi.fn(() => new Promise<void>((done) => { resolve = done }))
    const { wrapper } = setup({ save })
    await open(wrapper)
    await wrapper.get('input').setValue('Neu')
    await wrapper.get('input').trigger('keydown', { key: 'Enter' })
    await nextTick()
    expect(wrapper.get('[role="status"]').text()).toContain('Speichern')
    await wrapper.get('input').trigger('keydown', { key: 'Enter' })
    expect(save).toHaveBeenCalledTimes(1)
    resolve()
    await flushPromises()
    expect(wrapper.find('input').exists()).toBe(false)
  })

  it.each([
    [403, 'Berechtigung'], [404, 'nicht mehr'], [409, 'Konflikt'],
    [412, 'geändert'], [428, 'Versionsinformation'], [422, 'Ungültiger'],
  ])('retains draft on HTTP %i error', async (status, message) => {
    const save = vi.fn().mockRejectedValue(new ApiError(status, 'Failed', {}))
    const { wrapper } = setup({ save })
    await open(wrapper)
    await wrapper.get('input').setValue('Entwurf')
    await wrapper.get('input').trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain(message)
    expect((wrapper.get('input').element as HTMLInputElement).value).toBe('Entwurf')
  })

  it('allows retry after a transport failure without losing draft', async () => {
    const save = vi.fn().mockRejectedValueOnce(new Error('Netzwerk')).mockResolvedValue(undefined)
    const { wrapper } = setup({ save })
    await open(wrapper)
    await wrapper.get('input').setValue('Retry')
    await wrapper.get('input').trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('Netzwerk')
    await wrapper.get('input').trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(save).toHaveBeenCalledTimes(2)
    expect(wrapper.find('input').exists()).toBe(false)
  })

  it('prevents activating a second cell while the first draft cannot save', async () => {
    const coordinator = useInlineCellCoordinator()
    const fail = vi.fn().mockRejectedValue(new Error('Offline'))
    const first = setup({ id: 'first', coordinator, save: fail })
    const second = setup({ id: 'second', coordinator })
    await open(first.wrapper)
    await first.wrapper.get('input').setValue('Entwurf')
    await open(second.wrapper)
    expect(first.wrapper.find('input').exists()).toBe(true)
    expect(second.wrapper.find('input').exists()).toBe(false)
    expect(coordinator.activeId.value).toBe('first')
  })

  it('releases the active editor when permissions change', async () => {
    const { wrapper, coordinator } = setup()
    await open(wrapper)
    await wrapper.setProps({ editable: false })
    expect(coordinator.activeId.value).toBeNull()
    expect(wrapper.find('input').exists()).toBe(false)
  })

  it('supports a mobile div instead of table markup', async () => {
    const { wrapper } = setup({ as: 'div' })
    expect(wrapper.element.tagName).toBe('DIV')
    await open(wrapper)
    expect(wrapper.find('input').exists()).toBe(true)
  })
})
