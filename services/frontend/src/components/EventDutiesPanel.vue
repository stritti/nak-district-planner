<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ApiError, parseConflictError, type ConflictError, userMessage } from '../api/errors'
import {
  deleteDutyAssignment,
  getSlotDuties,
  listEligibleUsers,
  listLeaderChoices,
  listSuggestions,
  revalidateDutyAssignment,
  saveDutyAssignment,
  setSuggestionHidden,
  type DutyAssignment,
  type DutyCategory,
  type DutyLeaderChoice,
  type DutySuggestion,
  type EligibleUser,
} from '../api/eventDuties'

const props = defineProps<{
  districtId: string
  slotId: string
  congregationId?: string | null
  canEdit: boolean
}>()
const emit = defineEmits<{ mutated: [] }>()

const categories = ref<DutyCategory[]>([])
const assignments = ref<DutyAssignment[]>([])
const users = ref<EligibleUser[]>([])
const leaders = ref<DutyLeaderChoice[]>([])
const suggestions = ref<DutySuggestion[]>([])
const category = ref('')
const kind = ref('name')
const name = ref('')
const subject = ref('')
const leaderId = ref('')
const editing = ref<string>()
// Revision read when the edit started; a reload must not silently replace it.
const editingRevision = ref('')
// Overlap with another duty of the same person: blocks, or asks for confirmation (warnings only).
const pendingConflict = ref<ConflictError | null>(null)
const loading = ref(false)
const error = ref('')
let version = 0
let suggestionsVersion = 0

async function load() {
  const current = ++version
  categories.value = []
  assignments.value = []
  users.value = []
  leaders.value = []
  suggestions.value = []
  error.value = ''
  loading.value = true
  try {
    const data = await getSlotDuties(props.districtId, props.slotId, props.canEdit)
    if (current !== version) return
    categories.value = data.categories
    assignments.value = data.assignments
    category.value = data.categories[0]?.id ?? ''
    if (props.canEdit) {
      const choices = await listEligibleUsers(
        props.districtId,
        props.congregationId ?? undefined,
      )
      if (current === version) users.value = choices
      // A missing leader list only removes that option; the other identities still work.
      const choosable = await listLeaderChoices(props.districtId, props.slotId).catch(() => [])
      if (current === version) leaders.value = choosable
    }
  } catch (cause) {
    if (current === version) {
      error.value = cause instanceof Error
        ? cause.message
        : 'Dienste konnten nicht geladen werden'
    }
  } finally {
    if (current === version) loading.value = false
  }
}

watch(
  () => [props.districtId, props.slotId, props.congregationId, props.canEdit],
  () => {
    editing.value = undefined
    name.value = ''
    subject.value = ''
    void load()
  },
  { immediate: true },
)

// A confirmation belongs to the exact assignment that was rejected: any change of what
// would be sent withdraws it, so "Trotzdem zuweisen" never covers an unseen conflict.
watch([category, kind, name, subject, leaderId, editing], () => {
  pendingConflict.value = null
})

watch([category, () => props.districtId, () => props.congregationId], async () => {
  const current = ++suggestionsVersion
  suggestions.value = []
  if (!category.value || !props.canEdit) return
  try {
    const data = await listSuggestions(
      props.districtId,
      category.value,
      props.congregationId ?? undefined,
      true,
    )
    if (current === suggestionsVersion) suggestions.value = data
  } catch (cause) {
    if (current === suggestionsVersion) {
      error.value = cause instanceof Error
        ? cause.message
        : 'Namensvorschläge konnten nicht geladen werden'
    }
  }
})

interface ActionOptions<Result> {
  failure: string
  apply?: (result: Result) => void
  reload?: boolean
  mutated?: boolean
  /** Return true when the failure was handled and needs no generic message. */
  handleError?: (cause: unknown) => boolean
}

const STALE =
  'Der Eintrag wurde zwischenzeitlich geändert. Die Ansicht wurde aktualisiert – bitte erneut versuchen.'

function isStale(cause: unknown): boolean {
  return cause instanceof ApiError && (cause.status === 412 || cause.status === 428)
}

async function runAction<Result>(
  action: () => Promise<Result>,
  options: ActionOptions<Result>,
) {
  if (loading.value) return
  loading.value = true
  error.value = ''
  pendingConflict.value = null
  try {
    const result = await action()
    options.apply?.(result)
    if (options.mutated) emit('mutated')
    if (options.reload) await load()
  } catch (cause) {
    if (options.handleError?.(cause)) {
      // handled by the caller (for example an overlap that needs a decision)
    } else if (isStale(cause)) {
      // Reload first (it clears the error), then explain why the action did not apply.
      editing.value = undefined
      await load()
      error.value = STALE
    } else {
      error.value = userMessage(cause, options.failure)
    }
  } finally {
    loading.value = false
  }
}

function chosenIdentity(): string {
  if (kind.value === 'name') return name.value.trim()
  return kind.value === 'leader' ? leaderId.value : subject.value
}

async function save(confirmWarnings = false) {
  if (!category.value || !chosenIdentity()) return
  const confirmation = confirmWarnings ? { confirm_warnings: true } : {}
  const identity = kind.value === 'name'
    ? { duty_category_id: category.value, name: name.value.trim(), ...confirmation }
    : kind.value === 'leader'
      ? { duty_category_id: category.value, leader_id: leaderId.value, ...confirmation }
      : { duty_category_id: category.value, linked_user_sub: subject.value, ...confirmation }
  await runAction(
    () => saveDutyAssignment(
      props.districtId,
      props.slotId,
      identity,
      editing.value,
      editing.value ? editingRevision.value : undefined,
    ),
    {
      failure: 'Speichern fehlgeschlagen',
      apply: () => {
        name.value = ''
        subject.value = ''
        leaderId.value = ''
        editing.value = undefined
        editingRevision.value = ''
      },
      mutated: true,
      reload: true,
      handleError: (cause) => {
        const conflict = parseConflictError(cause)
        if (!conflict) return false
        pendingConflict.value = conflict
        return true
      },
    },
  )
}

async function remove(assignment: DutyAssignment) {
  await runAction(
    () => deleteDutyAssignment(props.districtId, assignment.id, assignment.revision),
    { failure: 'Entfernen fehlgeschlagen', mutated: true, reload: true },
  )
}

async function revalidate(assignment: DutyAssignment) {
  await runAction(
    () => revalidateDutyAssignment(props.districtId, assignment.id, assignment.revision),
    { failure: 'Bestätigung fehlgeschlagen', mutated: true, reload: true },
  )
}

async function hide(suggestion: DutySuggestion) {
  await runAction(
    () => setSuggestionHidden(
      props.districtId,
      suggestion.id,
      !suggestion.hidden,
      suggestion.revision,
    ),
    {
      failure: 'Änderung fehlgeschlagen',
      apply: updated => {
        suggestions.value = suggestions.value.map(item =>
          item.id === suggestion.id ? updated : item,
        )
      },
    },
  )
}

function edit(assignment: DutyAssignment) {
  editing.value = assignment.id
  editingRevision.value = assignment.revision
  category.value = assignment.duty_category_id
  kind.value = assignment.leader_id ? 'leader' : assignment.linked_user_sub ? 'account' : 'name'
  subject.value = assignment.linked_user_sub ?? ''
  leaderId.value = assignment.leader_id ?? ''
  name.value = assignment.display_name
}
</script>

<template>
  <section class="space-y-3 border-t pt-4" aria-label="Organisatorische Dienste">
    <h3 class="font-semibold">Organisatorische Dienste</h3>
    <p class="text-sm text-gray-500">
      Optional – freie Namen erhalten keinen persönlichen Kalender.
    </p>
    <p v-if="loading" role="status">Laden…</p>
    <p v-if="error" role="alert" class="text-red-600">{{ error }}</p>
    <div
      v-if="pendingConflict"
      role="alert"
      data-testid="duty-conflict"
      class="rounded border border-amber-300 bg-amber-50 p-2 text-sm text-amber-900"
    >
      <ul class="list-disc pl-5">
        <li v-for="item in pendingConflict.conflicts" :key="item.rule_id">{{ item.message }}</li>
      </ul>
      <button
        v-if="!pendingConflict.blocking.length"
        type="button"
        class="btn-secondary mt-2 px-3"
        data-testid="duty-conflict-confirm"
        @click="save(true)"
      >
        Trotzdem zuweisen
      </button>
    </div>

    <div v-for="assignment in assignments" :key="assignment.id" class="rounded border p-2 text-sm">
      <p>
        {{ assignment.duty_label }}: {{ assignment.display_name }}
        <span v-if="assignment.linked_user_sub">(Konto)</span>
        <span v-else-if="assignment.leader_id">(Amtsträger)</span>
      </p>
      <p v-if="assignment.needs_review" class="text-amber-700">Prüfung erforderlich</p>
      <p v-if="assignment.over_capacity" class="text-amber-700">Kapazität überschritten</p>
      <div v-if="canEdit" class="flex gap-3">
        <button
          v-if="assignment.quarantined"
          type="button"
          data-testid="revalidate-duty"
          :disabled="loading"
          class="text-blue-600"
          @click="revalidate(assignment)"
        >
          Geltungsbereich bestätigen
        </button>
        <button
          v-else
          type="button"
          :disabled="loading"
          class="text-blue-600"
          @click="edit(assignment)"
        >
          Neu zuordnen
        </button>
        <button
          type="button"
          data-testid="remove-duty"
          :disabled="loading"
          class="text-red-600"
          @click="remove(assignment)"
        >
          Entfernen
        </button>
      </div>
    </div>

    <form v-if="canEdit && categories.length" class="space-y-2" @submit.prevent="save()">
      <label class="block">
        Dienst
        <select v-model="category" class="form-input">
          <option v-for="item in categories" :key="item.id" :value="item.id">
            {{ item.label }} ({{ item.capacity }} Plätze)
          </option>
        </select>
      </label>
      <label class="block">
        Zuordnung
        <select v-model="kind" data-testid="identity-kind" class="form-input">
          <option value="name">Freier Name</option>
          <option value="account">Verknüpftes Konto</option>
          <option v-if="leaders.length" value="leader">Amtsträger</option>
        </select>
      </label>
      <label v-if="kind === 'name'" class="block">
        Name
        <input
          v-model="name"
          data-testid="duty-name"
          class="form-input"
          :list="`duty-names-${slotId}`"
          maxlength="200"
        />
        <datalist :id="`duty-names-${slotId}`">
          <option
            v-for="suggestion in suggestions.filter(item => !item.hidden)"
            :key="suggestion.id"
            :value="suggestion.display_name"
          />
        </datalist>
      </label>
      <label v-else-if="kind === 'leader'" class="block">
        Amtsträger
        <select v-model="leaderId" data-testid="duty-leader" class="form-input">
          <option value="">Amtsträger auswählen</option>
          <option v-for="leader in leaders" :key="leader.id" :value="leader.id">
            {{ leader.rank ? `${leader.rank} ` : '' }}{{ leader.name }}
          </option>
        </select>
      </label>
      <label v-else class="block">
        Konto
        <select v-model="subject" data-testid="duty-account" class="form-input">
          <option value="">Konto auswählen</option>
          <option v-for="user in users" :key="user.sub" :value="user.sub">
            {{ user.display_name }}
          </option>
        </select>
      </label>
      <button
        type="submit"
        class="btn-primary"
        :disabled="loading || !chosenIdentity()"
      >
        {{ editing ? 'Zuordnung ersetzen' : 'Dienst zuordnen' }}
      </button>
    </form>

    <details v-if="canEdit && suggestions.length">
      <summary class="cursor-pointer text-sm">Gespeicherte Namen verwalten</summary>
      <div
        v-for="suggestion in suggestions"
        :key="suggestion.id"
        class="flex gap-2 py-1 text-sm"
      >
        <span>{{ suggestion.display_name }}</span>
        <button
          type="button"
          class="text-blue-600"
          :disabled="loading"
          @click="hide(suggestion)"
        >
          {{ suggestion.hidden ? 'Wiederherstellen' : 'Ausblenden' }}
        </button>
      </div>
    </details>
  </section>
</template>
