import { defineStore } from 'pinia'
import { ref } from 'vue'

/** Persisted UI preferences are scoped to the OIDC subject, never to a session token. */
export const usePreferencesStore = defineStore('preferences', () => {
  const hiddenHelpByUser = ref<Record<string, string[]>>({})

  function hiddenHelp(userSub: string): readonly string[] {
    return hiddenHelpByUser.value[userSub] ?? []
  }

  function saveHiddenHelp(userSub: string, keys: readonly string[]): void {
    if (!userSub) return
    hiddenHelpByUser.value = {
      ...hiddenHelpByUser.value,
      [userSub]: [...new Set(keys)],
    }
  }

  return { hiddenHelpByUser, hiddenHelp, saveHiddenHelp }
}, {
  persist: { pick: ['hiddenHelpByUser'] },
})
