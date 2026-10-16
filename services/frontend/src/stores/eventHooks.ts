// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ApiError } from '../api/errors'
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

const STALE = 'Die Benachrichtigung wurde zwischenzeitlich geändert. Die Liste wurde aktualisiert – bitte erneut versuchen.'

const isStale = (cause: unknown) => cause instanceof ApiError && (cause.status === 412 || cause.status === 428)

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

  /** Re-reads the hooks after a stale write so the next attempt uses current revisions. */
  async function refresh(id: string) {
    try {
      const hooks = await listEventHooks(id)
      if (districtId.value === id) items.value = hooks
    } catch {
      // The stale-write message already asks the user to retry.
    }
  }

  const revisionOf = (hookId: string) => items.value.find(item => item.id === hookId)?.revision ?? ''

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
      if (isStale(cause)) {
        error.value = STALE
        await refresh(id)
      } else {
        error.value = message(cause, fallback)
      }
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

  /** `revision` is the one the caller read when it started editing; defaults to the listed one. */
  function update(hookId: string, input: EventHookInput, revision?: string) {
    return write(
      'Benachrichtigung konnte nicht gespeichert werden',
      id => updateEventHook(id, hookId, input, revision ?? revisionOf(hookId)),
      replace,
    )
  }

  function deactivate(hookId: string) {
    return write(
      'Benachrichtigung konnte nicht deaktiviert werden',
      id => deactivateEventHook(id, hookId, revisionOf(hookId)),
      replace,
    )
  }

  function placeholdersFor(eventType: string): string[] {
    return eventTypes.value.find(info => info.event_type === eventType)?.placeholders ?? []
  }

  return { items, eventTypes, loading, saving, error, districtId, load, create, update, deactivate, placeholdersFor }
})
