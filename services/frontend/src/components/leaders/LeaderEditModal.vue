<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
<div
  class="modal-backdrop"
  @click.self="emit('close')"
>
  <div class="modal-panel max-w-lg">
    <div class="flex items-center justify-between mb-4">
      <h2 class="modal-title">Amtstragende:n bearbeiten</h2>
      <button class="modal-close" @click="emit('close')">
        <XMarkIcon class="h-5 w-5" />
      </button>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
      <div class="col-span-1 sm:col-span-2">
        <label class="form-label">Name *</label>
        <input
          v-model="modal.name"
          type="text"
          class="form-input"
        />
      </div>

      <div>
        <label class="form-label">Grad *</label>
        <select
          v-model="modal.rank"
          class="form-input"
        >
          <option value="">Grad wählen…</option>
          <option v-for="r in LEADER_RANKS" :key="r.value" :value="r.value">{{ r.label }}</option>
        </select>
      </div>

      <div>
        <label class="form-label">E-Mail</label>
        <input
          v-model="modal.email"
          type="email"
          class="form-input"
        />
      </div>

      <div>
        <label class="form-label">Telefon</label>
        <input
          v-model="modal.phone"
          type="text"
          class="form-input"
        />
      </div>

      <div class="col-span-1 sm:col-span-2">
        <label class="form-label">Notizen</label>
        <textarea
          v-model="modal.notes"
          rows="2"
          class="form-input"
        />
      </div>
    </div>

    <fieldset class="mb-4" data-testid="assignments">
      <legend class="form-label">Zuordnungen</legend>
      <ul class="space-y-2">
        <li
          v-for="assignment in modal.assignments"
          :key="assignment.id"
          class="flex flex-wrap items-center gap-2 text-sm"
          :data-testid="`assignment-${assignment.id}`"
        >
          <span class="min-w-[8rem] font-medium text-gray-700 dark:text-gray-300">
            {{ levelLabel(assignment.congregation_id) }}
          </span>
          <span
            v-if="assignment.is_home"
            class="rounded bg-teal-100 px-1.5 py-0.5 text-xs text-teal-800 dark:bg-teal-900 dark:text-teal-200"
          >Heimat</span>
          <select
            :value="assignment.role ?? ''"
            class="form-input w-auto"
            :aria-label="`Beauftragung ${levelLabel(assignment.congregation_id)}`"
            :disabled="!canManage(assignment.congregation_id) || busy"
            @change="emit('assignment-role', assignment, ($event.target as HTMLSelectElement).value || null)"
          >
            <option value="">Keine</option>
            <option v-for="sr in roleChoicesFor(assignment.congregation_id)" :key="sr.value" :value="sr.value">
              {{ sr.label }}
            </option>
          </select>
          <button
            v-if="!assignment.is_home && modal.assignments.length > 1"
            type="button"
            class="btn-secondary px-2 py-1 text-xs"
            :disabled="!canManage(assignment.congregation_id) || busy"
            @click="emit('assignment-home', assignment)"
          >Als Heimat festlegen</button>
          <button
            v-if="!assignment.is_home"
            type="button"
            class="btn-secondary px-2 py-1 text-xs text-red-600"
            :disabled="!canManage(assignment.congregation_id) || busy"
            @click="emit('assignment-remove', assignment)"
          >Entfernen</button>
        </li>
      </ul>
      <div v-if="targets.length" class="mt-3 flex flex-wrap items-center gap-2 text-sm">
        <select v-model="modal.newAssignment.target" class="form-input w-auto" aria-label="Neue Zuordnung">
          <option value="">Zuordnung hinzufügen…</option>
          <option v-for="target in targets" :key="target.value" :value="target.value">{{ target.label }}</option>
        </select>
        <select
          v-model="modal.newAssignment.role"
          class="form-input w-auto"
          aria-label="Beauftragung der neuen Zuordnung"
        >
          <option :value="null">Keine</option>
          <option v-for="sr in newRoleChoices" :key="sr.value" :value="sr.value">{{ sr.label }}</option>
        </select>
        <button
          type="button"
          class="btn-secondary px-2 py-1 text-xs"
          :disabled="!modal.newAssignment.target || busy"
          @click="emit('assignment-add')"
        >Hinzufügen</button>
      </div>
    </fieldset>

    <label class="flex items-center gap-2 text-sm mb-4">
      <input v-model="modal.is_active" type="checkbox" class="rounded" />
      <span class="text-gray-700 dark:text-gray-300">Aktiv (für Dienstplan-Zuweisung verfügbar)</span>
    </label>

    <label class="flex items-center gap-2 text-sm mb-4">
      <input v-model="modal.hidden_from_lists" type="checkbox" class="rounded" />
      <span>Aus normalen Listen ausblenden</span>
    </label>
    <label class="block text-sm mb-4">Dienstende (einschließlich)
      <input v-model="modal.service_end_date" type="date" class="form-input" />
    </label>

    <p v-if="modal.error" class="text-sm text-red-600 dark:text-red-400 mb-3">{{ modal.error }}</p>

    <div class="flex justify-end gap-3">
      <button
        class="btn-secondary hover:bg-gray-50 dark:hover:bg-gray-800"
        @click="emit('close')"
      >
        Abbrechen
      </button>
      <button
        class="btn-primary px-4 py-2"
        :disabled="!modal.name.trim() || !modal.rank || saving"
        @click="emit('submit')"
      >
        <CheckIcon class="h-4 w-4" />
        {{ saving ? 'Speichern…' : 'Speichern' }}
      </button>
    </div>
  </div>
</div>
</template>

<script setup lang="ts">
import type { EditModalState } from './modalState'
import { CheckIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { computed } from 'vue'
import { LEADER_RANKS, type LeaderAssignment } from '../../api/leaders'
import { roleChoicesFor } from '../../api/leaderRoles'
import type { CongregationResponse } from '../../api/districts'

// The parent owns the form state (reactive object) and the save logic; this
// component only renders it. Aliasing the prop avoids prop-mutation lint noise
// for what is intentionally shared, parent-owned form state.
const props = defineProps<{
  modal: EditModalState
  congregations: CongregationResponse[]
  saving: boolean
  /** An assignment request is running. */
  busy?: boolean
  /** The user may change the assignment of this congregation (`null` = district level). */
  canManage: (congregationId: string | null) => boolean
}>()
const modal = props.modal
const emit = defineEmits<{
  close: []
  submit: []
  'assignment-add': []
  'assignment-role': [assignment: LeaderAssignment, role: string | null]
  'assignment-home': [assignment: LeaderAssignment]
  'assignment-remove': [assignment: LeaderAssignment]
}>()

function levelLabel(congregationId: string | null): string {
  if (congregationId === null) return 'Bezirksebene'
  return props.congregations.find((c) => c.id === congregationId)?.name ?? 'Gemeinde'
}

/** Levels the person is not yet assigned to and the user may manage. */
const targets = computed(() => {
  const taken = new Set(modal.assignments.map((a) => a.congregation_id))
  return [
    ...(taken.has(null) || !props.canManage(null) ? [] : [{ value: 'district', label: 'Bezirksebene' }]),
    ...props.congregations
      .filter((c) => !taken.has(c.id) && props.canManage(c.id))
      .map((c) => ({ value: c.id, label: c.name })),
  ]
})

const newRoleChoices = computed(() => {
  const { target } = modal.newAssignment
  return target ? roleChoicesFor(target === 'district' ? null : target) : []
})
</script>
