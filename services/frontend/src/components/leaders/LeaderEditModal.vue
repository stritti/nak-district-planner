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
        <label class="form-label">Besondere Beauftragung</label>
        <select
          v-model="modal.special_role"
          class="form-input"
        >
          <option :value="null">Keine</option>
          <option v-for="sr in SPECIAL_ROLES" :key="sr.value" :value="sr.value">{{ sr.label }}</option>
        </select>
      </div>

      <div>
        <label class="form-label">Gemeinde</label>
        <select
          v-model="modal.congregation_id"
          class="form-input"
        >
          <option :value="null">Bezirksebene</option>
          <option v-for="c in congregations" :key="c.id" :value="c.id">{{ c.name }}</option>
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
import { LEADER_RANKS, SPECIAL_ROLES } from '../../api/leaders'
import type { CongregationResponse } from '../../api/districts'

// The parent owns the form state (reactive object) and the save logic; this
// component only renders it. Aliasing the prop avoids prop-mutation lint noise
// for what is intentionally shared, parent-owned form state.
const props = defineProps<{
  modal: EditModalState
  congregations: CongregationResponse[]
  saving: boolean
}>()
const modal = props.modal
const emit = defineEmits<{ close: []; submit: [] }>()
</script>
