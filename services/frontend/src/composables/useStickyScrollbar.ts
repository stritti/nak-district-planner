import { computed, ref, type MaybeRefOrGetter, toValue } from 'vue'
import { useEventListener, useResizeObserver } from '@vueuse/core'

/**
 * A horizontal scrollbar that stays at the bottom edge of the viewport.
 *
 * The native scrollbar of a tall, wide container sits at the end of the content
 * and is out of sight while the container extends below the viewport. This
 * keeps a proxy scrollbar (`proxy`, rendered `sticky bottom-0` after the
 * container) in sync with the container's `scrollLeft`. Hide the container's
 * own scrollbar and size the proxy viewport to `viewportWidth` and its inner
 * content to `contentWidth`. This preserves the full scroll range even when a
 * classic vertical scrollbar reduces the container's usable width. Synchronize
 * scroll progress, not just pixel offsets, if browser scroll ranges differ.
 * Call `measure()` after the content changed without the container resizing.
 */
export function useStickyScrollbar(target: MaybeRefOrGetter<HTMLElement | null | undefined>) {
  const proxy = ref<HTMLElement | null>(null)
  const contentWidth = ref(0)
  const viewportWidth = ref(0)

  function measure() {
    const el = toValue(target)
    if (!el) return
    contentWidth.value = el.scrollWidth
    viewportWidth.value = el.clientWidth
  }

  function sync(from: HTMLElement | null | undefined, to: HTMLElement | null | undefined) {
    if (!from || !to) return

    // The effective scroll ranges can differ even at equal client widths:
    // classic scrollbar gutters and late layout updates may add extra space.
    // Synchronize progress instead of raw pixels so both ends are reachable.
    const fromRange = Math.max(0, from.scrollWidth - from.clientWidth)
    const toRange = Math.max(0, to.scrollWidth - to.clientWidth)
    const nextLeft = fromRange > 0 && toRange > 0
      ? Math.round(Math.min(1, Math.max(0, from.scrollLeft / fromRange)) * toRange)
      : from.scrollLeft

    if (to.scrollLeft !== nextLeft) to.scrollLeft = nextLeft
  }

  useResizeObserver(target, measure)
  useEventListener(target, 'scroll', () => sync(toValue(target), proxy.value), { passive: true })
  useEventListener(proxy, 'scroll', () => sync(proxy.value, toValue(target)), { passive: true })

  return {
    proxy,
    contentWidth,
    viewportWidth,
    needsScroll: computed(() => contentWidth.value > viewportWidth.value),
    measure,
  }
}
