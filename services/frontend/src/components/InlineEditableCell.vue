<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <component
    :is="as"
    ref="root"
    :tabindex="0"
    :aria-label="(editable ? label : label.split(':')[0]) + ': ' + (value || 'Leer') + (editable ? '. Enter oder F2 zum Bearbeiten' : '. Nur lesbar')"
    :data-inline-cell-id="id"
    :data-inline-editable="editable ? 'true' : undefined"
    :class="[
      as === 'td' ? 'table-td' : '',
      'focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600',
      editable ? 'cursor-text' : '',
    ]"
    @click="activate"
    @keydown="onCellKeydown"
    @focusout="onFocusOut"
  >
    <div v-if="editing" class="flex flex-col gap-1 min-w-[10rem]">
      <select
        v-if="choices"
        ref="selectInput"
        v-model="draft"
        :aria-label="label"
        :aria-invalid="!!error"
        :aria-describedby="error ? id + '-error' : undefined"
        class="w-full rounded border border-blue-500 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
        :disabled="saving"
        @keydown="onEditorKeydown"
      >
        <option value="">Auswählen…</option>
        <option v-for="choice in choices" :key="choice.value" :value="choice.value">
          {{ choice.label }}
        </option>
      </select>
      <input
        v-else
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
      <div v-if="remoteSnapshot" class="text-xs text-gray-600 dark:text-gray-300">
        Aktueller gespeicherter Wert: {{ remoteSnapshot.value || '—' }}. Dein Entwurf bleibt erhalten.
      </div>
      <button
        v-if="stale && reload"
        type="button"
        class="text-left text-xs text-blue-700 underline"
        :disabled="recovering"
        @click.stop.prevent="reloadLatest"
      >
        {{ recovering ? 'Lade aktuellen Stand…' : 'Aktuellen Stand zum Vergleichen laden' }}
      </button>
    </div>
    <span v-else class="block truncate" :title="displayValue ?? value ?? undefined">{{ displayValue ?? value ?? '—' }}</span>
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
  displayValue?: string | null
  choices?: { value: string; label: string }[]
  label: string
  editable: boolean
  coordinator: InlineCellCoordinator
  save: (draft: string, revision: string) => Promise<void>
  reload?: () => Promise<{ value: string | null | undefined; revision: string }>
  revision: string
  as?: 'td' | 'div'
  required?: boolean
  maxLength?: number
}>(), { as: 'td', required: false })

const root = ref<HTMLElement | null>(null)
const input = ref<HTMLInputElement | null>(null)
const selectInput = ref<HTMLSelectElement | null>(null)
const draft = ref(props.value ?? '')
const startingRevision = ref(props.revision)
const error = ref('')
const announcement = ref('')
const saving = ref(false)
const stale = ref(false)
const recovering = ref(false)
const remoteSnapshot = ref<{ value: string | null | undefined; revision: string } | null>(null)
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
  remoteSnapshot.value = null
  stale.value = false
  error.value = ''
  announcement.value = ''
  await nextTick()
  const editor = input.value ?? selectInput.value
  editor?.focus()
  if (editor instanceof HTMLInputElement) editor.select()
}

function cancel(): void {
  if (saving.value) return
  draft.value = props.value ?? ''
  remoteSnapshot.value = null
  stale.value = false
  error.value = ''
  props.coordinator.release(props.id)
  nextTick(() => root.value?.focus())
}

function saveError(cause: unknown): string {
  if (cause instanceof ApiError) {
    const detail = (cause.body as { detail?: unknown } | null)?.detail
    if (typeof detail === 'string' && detail.trim()) return detail
    const conflicts = (detail as { conflicts?: { message: string }[] } | undefined)?.conflicts
    if (conflicts?.length) return conflicts.map((item) => item.message).join(' ')
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
    const editor = input.value ?? selectInput.value
    editor?.focus()
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
      stale.value = cause instanceof ApiError && cause.status === 412
      announcement.value = error.value
      saving.value = false
      await nextTick()
      const editor = input.value ?? selectInput.value
      editor?.focus()
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

async function reloadLatest(): Promise<void> {
  if (!props.reload || recovering.value) return
  recovering.value = true
  try {
    const snapshot = await props.reload()
    if (!snapshot.revision) throw new Error('Versionsinformation fehlt. Bitte neu laden.')
    remoteSnapshot.value = snapshot
    startingRevision.value = snapshot.revision
    stale.value = false
    error.value = 'Aktueller Stand geladen. Bitte den Entwurf vergleichen und erneut speichern.'
  } catch (cause) {
    error.value = saveError(cause)
  } finally {
    recovering.value = false
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
    const scope = root.value?.closest('[data-inline-edit-scope]') ?? root.value?.closest('.card')
    const cells = Array.from(scope?.querySelectorAll<HTMLElement>('[data-inline-editable="true"]') ?? [])
      .filter((cell) => cell.getClientRects().length > 0)
    const index = cells.indexOf(root.value as HTMLElement)
    const destination = event.key === 'Tab' && index >= 0 ? cells[index + direction] : undefined
    if (!(await commit())) return
    await nextTick()
    if (!destination) {
      if (event.key === 'Tab') {
        const scopeElement = scope ?? root.value
        const focusable = Array.from(document.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'))
          .filter((element) => element.getClientRects().length > 0 && !element.closest('[inert]'))
        const currentIndex = focusable.indexOf(scopeElement as HTMLElement)
        const candidates = focusable.filter((element) => !scopeElement?.contains(element))
        const fromRoot = focusable.indexOf(root.value as HTMLElement)
        const origin = currentIndex >= 0 ? currentIndex : fromRoot
        const next = direction > 0
          ? candidates.find((element) => focusable.indexOf(element) > origin)
          : [...candidates].reverse().find((element) => focusable.indexOf(element) < origin)
        next?.focus()
      } else {
        root.value?.focus()
      }
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
