import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { useAuthStore } from './auth'
import { BrowserHelpPreferences, helpVisibilityKey } from '../help/preferences'
import type { HelpContext } from '../help/catalog'

/** User-scoped local preference storage; server-side preferences require a separate API. */
export const useHelpStore = defineStore('contextual-help', () => {
  const auth = useAuthStore()
  const identity = computed(() => auth.isAuthenticated ? (auth.user?.sub ? `user:${auth.user.sub}` : null) : 'guest')
  const hidden = ref<string[]>([])
  const storage = typeof localStorage === 'undefined' ? null : new BrowserHelpPreferences(localStorage)

  watch(identity, (current) => {
    hidden.value = current && storage ? [...storage.read(current).hidden] : []
  }, { immediate: true })

  function isHidden(helpId: string, context: HelpContext): boolean {
    return hidden.value.includes(helpVisibilityKey(helpId, context))
  }

  function save(keys: string[]) {
    if (!identity.value) return
    hidden.value = [...new Set(keys)]
    storage?.write(identity.value, { hidden: hidden.value })
  }

  function hide(helpId: string, context: HelpContext) {
    if (!identity.value) return
    save([...hidden.value, helpVisibilityKey(helpId, context)])
  }

  function restore(context: HelpContext) {
    const currentContext = (key: string): boolean => {
      try {
        const value: unknown = JSON.parse(key)
        return Array.isArray(value) && value.length === 2 && value[1] === context
      } catch {
        return false
      }
    }
    save(hidden.value.filter((key) => !currentContext(key)))
  }

  return { identity, hidden, isHidden, hide, restore }
})
