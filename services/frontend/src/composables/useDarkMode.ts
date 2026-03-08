import { onMounted, ref, watch } from 'vue'

const STORAGE_KEY = 'nak-planer-theme'

// Module-level singleton so all components share the same state
const isDark = ref(false)
let initialized = false

function applyTheme(dark: boolean) {
  if (typeof document !== 'undefined') {
    document.documentElement.classList.toggle('dark', dark)
  }
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, dark ? 'dark' : 'light')
  }
}

watch(isDark, applyTheme)

export function useDarkMode() {
  onMounted(() => {
    if (initialized) return
    initialized = true

    const stored = typeof localStorage !== 'undefined'
      ? localStorage.getItem(STORAGE_KEY)
      : null

    if (stored !== null) {
      isDark.value = stored === 'dark'
    } else if (typeof window !== 'undefined') {
      isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
    }
  })

  function toggle() {
    isDark.value = !isDark.value
  }

  return { isDark, toggle }
}
