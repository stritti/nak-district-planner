import type { HelpContext } from './catalog'

const PREFIX = 'nak-help-hidden:v1:'

export interface HelpPreferences {
  readonly hidden: readonly string[]
}

export interface HelpPreferencesStorage {
  read(identity: string): HelpPreferences
  write(identity: string, preferences: HelpPreferences): boolean
}

/** A storage key always includes both the help ID and the view context. */
export function helpVisibilityKey(helpId: string, context: HelpContext): string {
  return JSON.stringify([helpId, context])
}

/** Browser storage is only a local preference cache, not a backend user profile. */
export class BrowserHelpPreferences implements HelpPreferencesStorage {
  constructor(private readonly storage: Pick<Storage, 'getItem' | 'setItem'>) {}

  read(identity: string): HelpPreferences {
    try {
      const parsed: unknown = JSON.parse(this.storage.getItem(PREFIX + identity) ?? '{"hidden":[]}')
      if (!parsed || typeof parsed !== 'object' || !('hidden' in parsed)) return { hidden: [] }
      const hidden = (parsed as { hidden: unknown }).hidden
      return { hidden: Array.isArray(hidden) ? hidden.filter((key): key is string => typeof key === 'string') : [] }
    } catch {
      // Corrupted browser state or restricted storage must never block navigation.
      return { hidden: [] }
    }
  }

  write(identity: string, preferences: HelpPreferences): boolean {
    try {
      this.storage.setItem(PREFIX + identity, JSON.stringify({ hidden: [...new Set(preferences.hidden)] }))
      return true
    } catch {
      return false
    }
  }
}
