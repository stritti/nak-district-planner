import { onScopeDispose, ref, watch, type Ref } from 'vue'

const PREFIX = 'planner.view-settings.v1:'
const IDENTITY_KEY = PREFIX + 'identity'
const resetVersion = ref(0)

function storage(): Storage | undefined {
  try { return globalThis.sessionStorage } catch { return undefined }
}

/** Clear only view preferences; authentication and unrelated storage are untouched. */
export function clearSessionViewSettings() {
  const target = storage()
  try {
    if (target) {
      const keys = Array.from({ length: target.length }, (_, index) => target.key(index))
      for (const key of keys) if (key?.startsWith(PREFIX)) target.removeItem(key)
    }
  } catch { /* Blocked storage must not prevent logout. */ }
  resetVersion.value++
}

export function setSessionSettingsIdentity(identity: string | null) {
  const target = storage()
  try {
    const previous = target?.getItem(IDENTITY_KEY)
    if (previous && previous !== identity) clearSessionViewSettings()
  } catch { /* Views remain usable without session storage. */ }
}

interface SessionField {
  read: () => unknown
  restore: (value: unknown) => void
}

export function sessionField<T>(
  value: Ref<T>,
  defaults: () => T,
  valid: (candidate: unknown) => boolean,
): SessionField {
  return {
    read: () => value.value,
    restore: (candidate) => {
      value.value = valid(candidate) ? candidate as T : defaults()
    },
  }
}

export const sessionText = (value: unknown) => typeof value === 'string'
export const sessionDate = (value: unknown) =>
  typeof value === 'string' && (value === '' || (
    /^\d{4}-\d{2}-\d{2}$/.test(value) &&
    Number.isFinite(Date.parse(value)) &&
    new Date(value).toISOString().slice(0, 10) === value
  ))

/** Bind controls to one authenticated user, view and context within this tab. */
export function useSessionViewSettings(
  view: string,
  identity: () => string | null,
  context: () => string,
  fields: Record<string, SessionField>,
) {
  let restoring = false
  let activeKey: string | null = null
  const hasSavedSettings = ref(false)
  const stops = [
    watch(
      () => [identity(), context(), resetVersion.value] as const,
      ([user, scope, version], previous) => {
        restoring = true
        activeKey = user && scope ? PREFIX + JSON.stringify([user, view, scope]) : null
        let saved: Record<string, unknown> = {}
        hasSavedSettings.value = false
        try {
          const wasReset = previous && version !== previous[2]
          const raw = activeKey && !wasReset ? storage()?.getItem(activeKey) : null
          const parsed: unknown = raw ? JSON.parse(raw) : null
          if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
            saved = parsed as Record<string, unknown>
            hasSavedSettings.value = true
          }
        } catch { /* Missing or malformed settings use field defaults. */ }
        for (const [name, field] of Object.entries(fields)) field.restore(saved[name])
        restoring = false
      },
      { immediate: true, flush: 'sync' },
    ),
    watch(
      () => Object.fromEntries(Object.entries(fields).map(([name, field]) => [name, field.read()])),
      (settings) => {
        if (restoring || !activeKey) return
        try {
          const target = storage()
          target?.setItem(IDENTITY_KEY, identity() ?? '')
          target?.setItem(activeKey, JSON.stringify(settings))
        } catch {
          /* Saving preferences is optional, never a prerequisite for filtering. */
        }
      },
      { deep: true, flush: 'sync' },
    ),
  ]
  onScopeDispose(() => stops.forEach((stop) => stop()))
  return { hasSavedSettings }
}
