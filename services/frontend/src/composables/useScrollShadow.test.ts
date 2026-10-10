// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, expect, it } from 'vitest'
import { defineComponent, h, nextTick, ref } from 'vue'
import { mount } from '@vue/test-utils'
import { useScrollShadow } from './useScrollShadow'

async function scrollBox(scrollWidth: number, clientWidth: number) {
  let api!: ReturnType<typeof useScrollShadow>
  const wrapper = mount(
    defineComponent({
      setup() {
        const el = ref<HTMLElement | null>(null)
        api = useScrollShadow(el)
        return () => h('div', { ref: el })
      },
    }),
    { attachTo: document.body },
  )
  const el = wrapper.element as HTMLElement
  Object.defineProperty(el, 'scrollWidth', { configurable: true, value: scrollWidth })
  Object.defineProperty(el, 'clientWidth', { configurable: true, value: clientWidth })
  await nextTick() // useScroll attaches its listener after the render flush
  return { api, el, wrapper }
}

async function scrollTo(el: HTMLElement, left: number) {
  Object.defineProperty(el, 'scrollLeft', { configurable: true, value: left })
  el.dispatchEvent(new Event('scroll'))
  await nextTick()
}

describe('useScrollShadow', () => {
  it('shows no shadow when the content fits', async () => {
    const { api, wrapper } = await scrollBox(300, 300)
    api.measure()
    await nextTick()
    expect(api.showLeft.value).toBe(false)
    expect(api.showRight.value).toBe(false)
    wrapper.unmount()
  })

  it('shows only the right shadow at the start of overflowing content', async () => {
    const { api, wrapper } = await scrollBox(900, 300)
    api.measure()
    await nextTick()
    expect(api.showLeft.value).toBe(false)
    expect(api.showRight.value).toBe(true)
    wrapper.unmount()
  })

  it('shows both shadows in the middle and only the left one at the end', async () => {
    const { api, el, wrapper } = await scrollBox(900, 300)
    await scrollTo(el, 300)
    expect([api.showLeft.value, api.showRight.value]).toEqual([true, true])
    await scrollTo(el, 600)
    expect([api.showLeft.value, api.showRight.value]).toEqual([true, false])
    wrapper.unmount()
  })
})
