<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
<div
  class="modal-backdrop"
  @click.self="emit('close')"
>
  <div class="modal-panel max-w-lg">
    <div class="flex items-center justify-between mb-4">
      <h2 class="modal-title">Amtstragende:n hinzufügen</h2>
      <button class="modal-close" @click="emit('close')">
        <XMarkIcon class="h-5 w-5" />
      </button>
    </div>

    <div class="mb-4 px-3 py-2 bg-gray-50 dark:bg-gray-800 rounded text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1.5">
      <BuildingOffice2Icon v-if="modal.congregationId === null" class="h-3.5 w-3.5 text-indigo-400" />
      <HomeModernIcon v-else class="h-3.5 w-3.5 text-teal-400" />
      Ebene:
      <span class="font-medium text-gray-700 dark:text-gray-300">
        {{ modal.congregationId ? congregationLabel : 'Bezirksebene' }}
      </span>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
      <div class="col-span-1 sm:col-span-2">
        <label class="form-label">Name *</label>
        <input
          v-model="modal.name"
          type="text"
          class="form-input"
          placeholder="Vor- und Nachname"
          @input="modal.duplicates = []"
          @keyup.enter="emit('submit')"
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
          <option v-for="sr in roleChoicesFor(modal.congregationId)" :key="sr.value" :value="sr.value">{{ sr.label }}</option>
        </select>
      </div>

      <div>
        <label class="form-label">E-Mail</label>
        <input
          v-model="modal.email"
          type="email"
          class="form-input"
          placeholder="optional"
        />
      </div>

      <div>
        <label class="form-label">Telefon</label>
        <input
          v-model="modal.phone"
          type="text"
          class="form-input"
          placeholder="optional"
        />
      </div>
    </div>

    <div
      v-if="modal.duplicates.length"
      role="alert"
      data-testid="duplicate-leader-hint"
      class="mb-4 rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-100"
    >
      <p class="font-medium">Eine Person mit diesem Namen existiert bereits:</p>
      <ul class="mt-1 list-disc pl-5">
        <li v-for="match in modal.duplicates" :key="match.id">{{ match.label }}</li>
      </ul>
      <p class="mt-1">
        Bitte die vorhandene Person verwenden. Nur wenn es eine andere Person gleichen Namens ist,
        „Trotzdem neu anlegen“ wählen.
      </p>
    </div>

    <ErrorAlert v-if="modal.error" :message="modal.error" class="mb-3" />

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
        <PlusIcon class="h-4 w-4" />
        {{ saving ? 'Speichern…' : modal.duplicates.length ? 'Trotzdem neu anlegen' : 'Hinzufügen' }}
      </button>
    </div>
  </div>
</div>
</template>

<script setup lang="ts">
import type { AddModalState } from './modalState'
import { BuildingOffice2Icon, HomeModernIcon, PlusIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { LEADER_RANKS } from '../../api/leaders'
import { roleChoicesFor } from '../../api/leaderRoles'
import ErrorAlert from '../ErrorAlert.vue'

// The parent owns the form state (reactive object) and the save logic; this
// component only renders it. Aliasing the prop avoids prop-mutation lint noise
// for what is intentionally shared, parent-owned form state.
const props = defineProps<{
  modal: AddModalState
  congregationLabel: string
  saving: boolean
}>()
const modal = props.modal
const emit = defineEmits<{ close: []; submit: [] }>()
</script>
