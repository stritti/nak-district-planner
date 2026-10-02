import { computed, type MaybeRefOrGetter } from 'vue'
import { useResizeObserver, useScroll } from '@vueuse/core'

/**
 * Horizontal scroll hints for wide containers such as the matrix table.
 *
 * A shadow is shown on each side that still hides content. `useScroll`
 * reports both edges as reached when the content fits, so no shadow appears.
 * Call `measure()` after the content changed without the container resizing.
 */
export function useScrollShadow(target: MaybeRefOrGetter<HTMLElement | null | undefined>) {
  const { arrivedState, measure } = useScroll(target)
  useResizeObserver(target, measure)

  return {
    showLeft: computed(() => !arrivedState.left),
    showRight: computed(() => !arrivedState.right),
    measure,
  }
}
