<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <component
    :is="as"
    ref="root"
    :tabindex="editable ? 0 : undefined"
    :aria-label="editable ? label + ': ' + (value || 'Leer') + '. Enter oder F2 zum Bearbeiten' : undefined"
    :data-inline-cell-id="id"
    :data-inline-editable="editable ? 'true' : undefined"
    :class="[
      as === 'td' ? 'table-td' : '',
      editable ? 'cursor-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600' : '',
    ]"
    @click="activate"
    @keydown="onCellKeydown"
    @focusout="onFocusOut"
  >
    <div v-if="editing" class="flex flex-col gap-1 min-w-[10rem]">
      <input
        ref="input"
        v-model="draft"
        type="text"
        :aria-label="label"
        :aria-invalid="!!error"
        :aria-describedby="error ? id + '-error' : undefined"
        :maxlength="maxLength"
        class="w-full min-w-0 rounded border border-blue-500 bg-white dark:bg-gray-800 px-2 py-1 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-600"
        :disabled="saving"
        @keydown="onEditorKeydown"
      />
      <span v-if="saving" role="status" class="text-xs text-blue-700">Speichern…</span>
      <span v-if="error" :id="id + '-error'" role="alert" class="text-xs text-red-700">{{ error }}</span>
    </div>
    <span v-else class="block truncate" :title="value || undefined">{{ value || '—' }}</span>
    <span class="sr-only" aria-live="polite">{{ announcement }}</span>
  </component>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { ApiError } from '../api/errors'
import type { InlineCellCoordinator } from '../composables/useInlineCellCoordinator'

const props = withDefaults(defineProps<{
  id: string
  value: string | null | undefined
  label: string
  editable: boolean
  coordinator: InlineCellCoordinator
  save: (draft: string, revision: string) => Promise<void>
  revision: string
  as?: 'td' | 'div'
  required?: boolean
  maxLength?: number
}>(), { as: 'td', required: false })

const root = ref<HTMLElement | null>(null)
const input = ref<HTMLInputElement | null>(null)
const draft = ref(props.value ?? '')
const startingRevision = ref(props.revision)
const error = ref('')
const announcement = ref('')
const saving = ref(false)
const editing = computed(() => props.coordinator.activeId.value === props.id)
let pendingSave: Promise<boolean> | null = null

watch(() => props.value, (value) => {
  if (!editing.value) draft.value = value ?? ''
})
watch(() => props.editable, (allowed) => {
  if (!allowed) props.coordinator.release(props.id)
})
onBeforeUnmount(() => props.coordinator.release(props.id))

async function activate(): Promise<void> {
  if (!props.editable || editing.value) return
  if (!(await props.coordinator.activate(props.id, commit))) return
  draft.value = props.value ?? ''
  startingRevision.value = props.revision
  error.value = ''
  announcement.value = ''
  await nextTick()
  input.value?.focus()
  input.value?.select()
}

function cancel(): void {
  if (saving.value) return
  draft.value = props.value ?? ''
  error.value = ''
  props.coordinator.release(props.id)
  nextTick(() => root.value?.focus())
}

function saveError(cause: unknown): string {
  if (cause instanceof ApiError) {
    const detail = (cause.body as { detail?: unknown } | null)?.detail
    if (typeof detail === 'string' && detail.trim()) return detail
    if (cause.status === 412) return 'Der Eintrag wurde geändert. Bitte neu laden und vergleichen.'
    if (cause.status === 428) return 'Die Versionsinformation fehlt. Bitte neu laden.'
    if (cause.status === 403) return 'Keine Berechtigung zum Bearbeiten.'
    if (cause.status === 404) return 'Der Eintrag ist nicht mehr vorhanden.'
    if (cause.status === 409) return 'Konflikt: Änderung konnte nicht gespeichert werden.'
    if (cause.status === 422 || cause.status === 400) return 'Ungültiger Wert. Bitte Eingabe prüfen.'
  }
  return cause instanceof Error ? cause.message : 'Speichern fehlgeschlagen. Erneut versuchen.'
}

async function commit(): Promise<boolean> {
  if (pendingSave) return pendingSave
  if (!editing.value) return true
  const nextValue = draft.value.trim()
  if (props.required && !nextValue) {
    error.value = 'Dieses Feld darf nicht leer sein.'
    input.value?.focus()
    return false
  }
  if (props.maxLength && nextValue.length > props.maxLength) {
    error.value = 'Der Wert ist zu lang.'
    input.value?.focus()
    return false
  }
  if (nextValue === (props.value ?? '')) {
    props.coordinator.release(props.id)
    return true
  }
  pendingSave = (async () => {
    saving.value = true
    error.value = ''
    try {
      await props.save(nextValue, startingRevision.value)
      announcement.value = 'Gespeichert'
      props.coordinator.release(props.id)
      return true
    } catch (cause) {
      error.value = saveError(cause)
      announcement.value = error.value
      await nextTick()
      input.value?.focus()
      return false
    } finally {
      saving.value = false
    }
  })()
  try {
    return await pendingSave
  } finally {
    pendingSave = null
  }
}

async function onEditorKeydown(event: KeyboardEvent): Promise<void> {
  if (event.key === 'Escape') {
    event.preventDefault()
    event.stopPropagation()
    cancel()
  } else if (event.key === 'Enter' || event.key === 'Tab') {
    event.preventDefault()
    event.stopPropagation()
    const direction = event.shiftKey ? -1 : 1
    // Only navigate inside the same visible representation (table or mobile cards).
    const scope = root.value?.closest('[data-inline-edit-scope]')
    const cells = Array.from(scope?.querySelectorAll<HTMLElement>('[data-inline-editable="true"]') ?? [])
      .filter((cell) => cell.getClientRects().length > 0)
    const index = cells.indexOf(root.value as HTMLElement)
    const destination = event.key === 'Tab' && index >= 0 ? cells[index + direction] : undefined
    if (!(await commit())) return
    await nextTick()
    if (!destination) {
      root.value?.focus()
      return
    }
    destination.focus()
    destination.click()
  }
}

function onCellKeydown(event: KeyboardEvent): void {
  if (event.target !== root.value || !props.editable) return
  if (event.key === 'Enter' || event.key === 'F2') {
    event.preventDefault()
    void activate()
  }
}

function onFocusOut(event: FocusEvent): void {
  if (!editing.value || (event.relatedTarget instanceof Node && root.value?.contains(event.relatedTarget))) return
  void commit()
}
</script>
