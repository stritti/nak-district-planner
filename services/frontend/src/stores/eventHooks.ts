import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  createEventHook,
  deactivateEventHook,
  listEventHooks,
  listEventTypes,
  updateEventHook,
  type EventHook,
  type EventHookCreateInput,
  type EventHookInput,
  type EventTypeInfo,
} from '../api/eventHooks'

function message(cause: unknown, fallback: string): string {
  return cause instanceof Error && cause.message ? cause.message : fallback
}

export const useEventHooksStore = defineStore('event-hooks', () => {
  const items = ref<EventHook[]>([])
  const eventTypes = ref<EventTypeInfo[]>([])
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)
  const districtId = ref<string | null>(null)

  async function load(id: string) {
    districtId.value = id
    loading.value = true
    error.value = null
    items.value = []
    try {
      const [hooks, types] = await Promise.all([listEventHooks(id), listEventTypes(id)])
      // Ignore responses for a district the user has already navigated away from.
      if (districtId.value !== id) return
      items.value = hooks
      eventTypes.value = types
    } catch (cause) {
      if (districtId.value === id) error.value = message(cause, 'Benachrichtigungen konnten nicht geladen werden')
    } finally {
      if (districtId.value === id) loading.value = false
    }
  }

  /** Runs a write for the current district; errors are shown and rethrown. */
  async function write<T>(fallback: string, operation: (id: string) => Promise<T>, apply: (result: T) => void) {
    if (!districtId.value) throw new Error('Kein Bezirk ausgewählt')
    const id = districtId.value
    saving.value = true
    error.value = null
    try {
      const result = await operation(id)
      if (districtId.value === id) apply(result)
    } catch (cause) {
      error.value = message(cause, fallback)
      throw cause
    } finally {
      saving.value = false
    }
  }

  const replace = (hook: EventHook) => {
    items.value = items.value.map(item => (item.id === hook.id ? hook : item))
  }

  function create(input: EventHookCreateInput) {
    return write('Benachrichtigung konnte nicht angelegt werden', id => createEventHook(id, input), hook => {
      items.value.push(hook)
    })
  }

  function update(hookId: string, input: EventHookInput) {
    return write('Benachrichtigung konnte nicht gespeichert werden', id => updateEventHook(id, hookId, input), replace)
  }

  function deactivate(hookId: string) {
    return write('Benachrichtigung konnte nicht deaktiviert werden', id => deactivateEventHook(id, hookId), () => {
      items.value = items.value.map(item => (item.id === hookId ? { ...item, is_active: false } : item))
    })
  }

  function placeholdersFor(eventType: string): string[] {
    return eventTypes.value.find(info => info.event_type === eventType)?.placeholders ?? []
  }

  return { items, eventTypes, loading, saving, error, districtId, load, create, update, deactivate, placeholdersFor }
})
