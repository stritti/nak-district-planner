import { effectScope, ref, watch } from 'vue'

const STORAGE_KEY = 'nak-planer-theme'

// Module-level singleton — state shared across all component instances
const isDark = ref(false)

/** Read persisted theme, falling back to the OS preference on any error. */
function readStorage(): boolean | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored !== null) return stored === 'dark'
  } catch {
    // Storage may be disabled or quota exceeded; fall through to OS preference.
  }
  return null
}

/** Persist the chosen theme, ignoring any storage errors. */
function writeStorage(dark: boolean): void {
  try {
    localStorage.setItem(STORAGE_KEY, dark ? 'dark' : 'light')
  } catch {
    // Ignore write errors (private browsing, quota, …)
  }
}

// Synchronous initialization (SSR-guarded): apply the correct theme before
// the first render so there is no flash of the wrong theme.
if (typeof window !== 'undefined') {
  const stored = readStorage()
  isDark.value = stored !== null
    ? stored
    : window.matchMedia('(prefers-color-scheme: dark)').matches
  document.documentElement.classList.toggle('dark', isDark.value)
}

// Keep a reference to the scope so it can be torn down during Vite HMR.
const scope = effectScope(true)

// Register the watcher in a detached effectScope so it persists
// independently of any component's lifetime (not torn down on unmount).
scope.run(() => {
  watch(isDark, (dark) => {
    if (typeof document !== 'undefined') {
      document.documentElement.classList.toggle('dark', dark)
    }
    writeStorage(dark)
  })
})

// During Vite HMR the module is re-evaluated; stop the old watcher first
// to avoid duplicate side effects.
if (import.meta.hot) {
  import.meta.hot.dispose(() => scope.stop())
}

export function useDarkMode() {
  function toggle() {
    isDark.value = !isDark.value
  }

  return { isDark, toggle }
}
