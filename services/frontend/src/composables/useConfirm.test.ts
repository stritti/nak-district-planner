// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { afterEach, describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { useConfirm, useConfirmHost } from './useConfirm'
import ConfirmHost from '../components/ConfirmHost.vue'

const request = { title: 'Absagen?', message: 'Wirklich absagen?', variant: 'warning' as const }

describe('useConfirm', () => {
  afterEach(() => {
    useConfirmHost().cancel()
  })

  it('resolves true when the user confirms', async () => {
    const host = useConfirmHost()
    const answer = useConfirm()(request)

    expect(host.isRevealed.value).toBe(true)
    expect(host.options.value).toEqual(request)
    host.confirm()

    await expect(answer).resolves.toBe(true)
    expect(host.isRevealed.value).toBe(false)
  })

  it('resolves false when the user cancels', async () => {
    const answer = useConfirm()(request)
    useConfirmHost().cancel()
    await expect(answer).resolves.toBe(false)
  })

  it('cancels a pending request when a new one is opened', async () => {
    const confirm = useConfirm()
    const first = confirm(request)
    const second = confirm({ title: 'Zweite Frage', message: '?' })

    await expect(first).resolves.toBe(false)
    expect(useConfirmHost().options.value?.title).toBe('Zweite Frage')
    useConfirmHost().confirm()
    await expect(second).resolves.toBe(true)
  })
})

describe('ConfirmHost', () => {
  afterEach(() => {
    useConfirmHost().cancel()
  })

  it('renders nothing until a confirmation is requested', () => {
    const wrapper = mount(ConfirmHost, { global: { stubs: { Teleport: true } } })
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  })

  it('shows the requested dialog and resolves through its buttons', async () => {
    const wrapper = mount(ConfirmHost, { global: { stubs: { Teleport: true } } })
    const answer = useConfirm()({ ...request, confirmText: 'Absagen', variant: 'info' })
    await flushPromises()

    expect(wrapper.text()).toContain('Wirklich absagen?')
    const confirmButton = wrapper.findAll('button').find((b) => b.text() === 'Absagen')
    await confirmButton!.trigger('click')

    await expect(answer).resolves.toBe(true)
  })
})
