import { effectScope, ref, watch } from 'vue'

const STORAGE_KEY = 'nak-planer-theme'

// Module-level singleton — state shared across all component instances
const isDark = ref(false)

// Synchronous initialization (SSR-guarded): apply the correct theme before
// the first render so there is no flash of the wrong theme.
if (typeof window !== 'undefined') {
  const stored = localStorage.getItem(STORAGE_KEY)
  isDark.value = stored !== null
    ? stored === 'dark'
    : window.matchMedia('(prefers-color-scheme: dark)').matches
  document.documentElement.classList.toggle('dark', isDark.value)
}

// Register the watcher in a detached effectScope so it persists
// independently of any component's lifetime (not torn down on unmount).
effectScope(true).run(() => {
  watch(isDark, (dark) => {
    if (typeof document !== 'undefined') {
      document.documentElement.classList.toggle('dark', dark)
    }
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, dark ? 'dark' : 'light')
    }
  })
})

export function useDarkMode() {
  function toggle() {
    isDark.value = !isDark.value
  }

  return { isDark, toggle }
}
