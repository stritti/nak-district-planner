import { describe, expect, it } from 'vitest'
import { defineComponent, h, nextTick, ref } from 'vue'
import { mount } from '@vue/test-utils'
import { useStickyScrollbar } from './useStickyScrollbar'

function mountHost(sizes: { scrollWidth: number; clientWidth: number }) {
  let api!: ReturnType<typeof useStickyScrollbar>
  const Host = defineComponent({
    setup() {
      const container = ref<HTMLElement | null>(null)
      api = useStickyScrollbar(container)
      return () =>
        h('div', [
          h('div', { ref: container, 'data-testid': 'container' }),
          h('div', { ref: api.proxy, 'data-testid': 'proxy' }),
        ])
    },
  })
  const wrapper = mount(Host, { attachTo: document.body })
  const container = wrapper.get('[data-testid="container"]').element as HTMLElement
  const proxy = wrapper.get('[data-testid="proxy"]').element as HTMLElement
  // jsdom does not implement scrolling: back scrollLeft with a plain value.
  for (const el of [container, proxy]) {
    let left = 0
    Object.defineProperty(el, 'scrollLeft', {
      get: () => left,
      set: (value: number) => { left = value },
      configurable: true,
    })
  }
  Object.defineProperty(container, 'scrollWidth', { value: sizes.scrollWidth, configurable: true })
  Object.defineProperty(container, 'clientWidth', { value: sizes.clientWidth, configurable: true })
  return { wrapper, container, proxy, api }
}

describe('useStickyScrollbar', () => {
  it('is only needed when the content is wider than the container', async () => {
    const wide = mountHost({ scrollWidth: 2000, clientWidth: 800 })
    wide.api.measure()
    await nextTick()
    expect(wide.api.needsScroll.value).toBe(true)
    expect(wide.api.contentWidth.value).toBe(2000)
    expect(wide.api.viewportWidth.value).toBe(800)

    const narrow = mountHost({ scrollWidth: 800, clientWidth: 800 })
    narrow.api.measure()
    await nextTick()
    expect(narrow.api.needsScroll.value).toBe(false)
  })

  it('tracks a smaller client viewport when a classic vertical scrollbar appears', async () => {
    const { api, container, wrapper } = mountHost({ scrollWidth: 2000, clientWidth: 800 })
    api.measure()
    expect(api.viewportWidth.value).toBe(800)

    // The scrollbar uses 15px of the content width without shrinking scrollWidth.
    Object.defineProperty(container, 'clientWidth', { value: 785, configurable: true })
    api.measure()
    await nextTick()
    expect(api.viewportWidth.value).toBe(785)
    expect(api.contentWidth.value - api.viewportWidth.value).toBe(1215)
    expect(api.needsScroll.value).toBe(true)
    wrapper.unmount()
  })

  it('keeps container and proxy scroll positions in sync both ways', async () => {
    const { container, proxy } = mountHost({ scrollWidth: 2000, clientWidth: 800 })
    await nextTick() // listeners attach once the template refs are set

    container.scrollLeft = 120
    container.dispatchEvent(new Event('scroll'))
    expect(proxy.scrollLeft).toBe(120)

    proxy.scrollLeft = 300
    proxy.dispatchEvent(new Event('scroll'))
    expect(container.scrollLeft).toBe(300)
  })
})
