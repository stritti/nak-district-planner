<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
<div
  class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
  @click.self="emit('close')"
>
  <div class="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-base font-semibold text-gray-900">Registrierung genehmigen</h2>
      <button class="p-1 rounded hover:bg-gray-100 text-gray-400" @click="emit('close')">
        <XMarkIcon class="h-5 w-5" />
      </button>
    </div>
    <p class="text-sm text-gray-600 mb-4">
      <strong>{{ modal.name }}</strong> ({{ modal.email }}) wird als Amtstragende:r hinzugefügt.
      Sie können Grad und Gemeinde vor der Genehmigung anpassen.
    </p>
    <div class="space-y-3 mb-4">
      <div>
        <label class="form-label">Rolle</label>
        <select v-model="modal.role" class="form-select w-full">
          <option value="DISTRICT_ADMIN">DISTRICT_ADMIN</option>
          <option value="CONGREGATION_ADMIN">CONGREGATION_ADMIN</option>
          <option value="PLANNER">PLANNER</option>
          <option value="VIEWER">VIEWER</option>
        </select>
      </div>
      <div>
        <label class="form-label">Geltungsbereich</label>
        <select v-model="modal.scope_type" class="form-select w-full">
          <option value="DISTRICT">Bezirk</option>
          <option value="CONGREGATION">Gemeinde</option>
        </select>
      </div>
      <div>
        <label class="form-label">Grad</label>
        <select v-model="modal.rank" class="form-select w-full">
          <option :value="null">— kein Grad —</option>
          <option v-for="r in LEADER_RANKS" :key="r.value" :value="r.value">{{ r.label }}</option>
        </select>
      </div>
      <div>
        <label class="form-label">Gemeinde</label>
        <select v-model="modal.congregation_id" class="form-select w-full">
          <option :value="null">— Bezirksebene —</option>
          <option v-for="c in congregations" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>
      <div>
        <label class="form-label">Beauftragung</label>
        <select v-model="modal.special_role" class="form-select w-full">
          <option :value="null">— keine —</option>
          <option v-for="r in SPECIAL_ROLES" :key="r.value" :value="r.value">{{ r.label }}</option>
        </select>
      </div>
    </div>
    <p v-if="modal.error" class="text-sm text-red-600 mb-3">{{ modal.error }}</p>
    <div class="flex justify-end gap-3">
      <button
        class="text-sm px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
        @click="emit('close')"
      >Abbrechen</button>
      <button
        class="text-sm px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
        :disabled="saving"
        @click="emit('submit')"
      >Genehmigen</button>
    </div>
  </div>
</div>
</template>

<script setup lang="ts">
import type { ApproveModalState } from './modalState'
import { XMarkIcon } from '@heroicons/vue/24/outline'
import { LEADER_RANKS, SPECIAL_ROLES } from '../../api/leaders'
import type { CongregationResponse } from '../../api/districts'

// The parent owns the form state (reactive object) and the save logic; this
// component only renders it. Aliasing the prop avoids prop-mutation lint noise
// for what is intentionally shared, parent-owned form state.
const props = defineProps<{
  modal: ApproveModalState
  congregations: CongregationResponse[]
  saving: boolean
}>()
const modal = props.modal
const emit = defineEmits<{ close: []; submit: [] }>()
</script>
