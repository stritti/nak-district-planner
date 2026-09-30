import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { useAuthStore } from './auth'
import { usePreferencesStore } from './preferences'
import { BrowserHelpPreferences, helpVisibilityKey } from '../help/preferences'
import type { HelpContext } from '../help/catalog'

/** Guest help state is browser-local; signed-in state lives in the persisted preferences store. */
export const useHelpStore = defineStore('contextual-help', () => {
  const auth = useAuthStore()
  const preferences = usePreferencesStore()
  const identity = computed(() => auth.isAuthenticated ? (auth.user?.sub ? `user:${auth.user.sub}` : null) : 'guest')
  const hidden = ref<string[]>([])
  const guestStorage = typeof localStorage === 'undefined' ? null : new BrowserHelpPreferences(localStorage)

  watch([identity, () => preferences.hiddenHelpByUser], ([current]) => {
    if (current === 'guest') {
      hidden.value = guestStorage ? [...guestStorage.read('guest').hidden] : []
    } else if (current) {
      hidden.value = [...preferences.hiddenHelp(current.slice('user:'.length))]
    } else {
      hidden.value = []
    }
  }, { immediate: true })

  function isHidden(helpId: string, context: HelpContext): boolean {
    return hidden.value.includes(helpVisibilityKey(helpId, context))
  }

  function save(keys: string[]): void {
    const current = identity.value
    if (!current) return
    hidden.value = [...new Set(keys)]
    if (current === 'guest') guestStorage?.write('guest', { hidden: hidden.value })
    else preferences.saveHiddenHelp(current.slice('user:'.length), hidden.value)
  }

  function hide(helpId: string, context: HelpContext): void {
    if (!identity.value) return
    save([...hidden.value, helpVisibilityKey(helpId, context)])
  }

  function restore(context: HelpContext): void {
    const isCurrentContext = (key: string): boolean => {
      try {
        const parsed: unknown = JSON.parse(key)
        return Array.isArray(parsed) && parsed.length === 2 && parsed[1] === context
      } catch {
        return false
      }
    }
    save(hidden.value.filter((key) => !isCurrentContext(key)))
  }

  return { identity, hidden, isHidden, hide, restore }
})
